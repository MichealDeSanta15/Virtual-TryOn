"""One model worker, one pending request, bounded history, explicit cancellation."""
from collections import OrderedDict
import queue
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Job:
    id: str
    request: dict
    state: str = "queued"
    submitted: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None
    result: object = None
    error: str | None = None
    cancelled: bool = False


class BusyError(RuntimeError):
    pass


class TryOnWorker:
    def __init__(self, run, history=20):
        self.run = run
        self.history = history
        self.jobs = OrderedDict()
        self.lock = threading.RLock()
        self.pending = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, name="tryon-worker", daemon=True)
        self.thread.start()

    def submit(self, **request):
        with self.lock:
            if self.stop_event.is_set():
                raise BusyError("Worker is shutting down")
            if self.pending.full():
                raise BusyError("One request is already waiting. Wait or cancel it first.")
            job = Job(uuid.uuid4().hex, request)
            self.jobs[job.id] = job
            self.pending.put_nowait(job)
            self._prune()
            return job.id

    def _prune(self):
        done = [key for key, job in self.jobs.items() if job.finished is not None]
        while len(self.jobs) > self.history and done:
            del self.jobs[done.pop(0)]

    def get(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            # Public metadata only; do not copy a full PIL image at every poll.
            return {"id": job.id, "state": job.state, "submitted": job.submitted,
                    "started": job.started, "finished": job.finished,
                    "result": job.result, "error": job.error,
                    "cancel_requested": job.cancelled}

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            if job.finished is None:
                job.cancelled = True
                # Active diffusion is not interrupted at unsafe CUDA boundaries.
                if job.state == "queued":
                    job.state = "cancelling"

    def _stage(self, job, stage):
        with self.lock:
            job.state = "cancelling" if job.cancelled else stage

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                job = self.pending.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                with self.lock:
                    cancelled = job.cancelled
                    job.started = time.time()
                    job.state = "running"
                if not cancelled:
                    result = self.run(progress=lambda s: self._stage(job, s), **job.request)
                    with self.lock:
                        job.result = None if job.cancelled else result
                with self.lock:
                    job.state = "cancelled" if job.cancelled else "done"
            except Exception as exc:
                logging.getLogger(__name__).exception("Try-on job %s failed", job.id)
                with self.lock:
                    job.error = f"{type(exc).__name__}: {exc}"
                    job.state = "cancelled" if job.cancelled else "failed"
            finally:
                with self.lock:
                    job.finished = time.time()
                    job.request = {}  # release captured frames / image buffers
                    self._prune()
                self.pending.task_done()

    def close(self, timeout=2):
        self.stop_event.set()
        with self.lock:
            for job in self.jobs.values():
                if job.finished is None:
                    job.cancelled = True
        while True:
            try:
                job = self.pending.get_nowait()
                with self.lock:
                    job.state = "cancelled"
                    job.finished = time.time()
                    job.request = {}
                self.pending.task_done()
            except queue.Empty:
                break
        self.thread.join(timeout=timeout)
        return not self.thread.is_alive()
