"""Latest-frame capture. Frames are BGR; slow AI never backs up video queues."""
import threading
import time
import cv2


ORIENTATIONS = ('source', 'portrait_cw', 'portrait_ccw', 'cw90', 'ccw90', '180')


def rotation_for_shape(shape, orientation):
    """Clockwise degrees. Portrait modes use dimensions, NOT a phone tilt sensor."""
    if orientation not in ORIENTATIONS:
        raise ValueError('Unknown camera orientation')
    h, w = shape[:2]
    if orientation in ('portrait_cw', 'portrait_ccw'):
        return (90 if orientation == 'portrait_cw' else 270) if w > h else 0
    return {'source':0, 'cw90':90, 'ccw90':270, '180':180}[orientation]


def orient_frame(frame, orientation):
    """Copy/rotate pixels without stretching, cropping, mirroring or modifying input."""
    degrees = rotation_for_shape(frame.shape, orientation)
    if not degrees:
        return frame.copy()
    flag = {90:cv2.ROTATE_90_CLOCKWISE, 180:cv2.ROTATE_180, 270:cv2.ROTATE_90_COUNTERCLOCKWISE}[degrees]
    return cv2.rotate(frame, flag)


class LatestFrame:
    def __init__(self):
        self._condition = threading.Condition()
        self._frame = None
        self.sequence = 0
        self.timestamp = 0.0
        self.received = 0
        self.started = time.monotonic()
        self.source = "none"
        self.error = None
        self.closed = False
        self.orientation = "source"
        self.orientation_revision = 0

    def set_orientation(self, orientation):
        if orientation not in ORIENTATIONS:
            raise ValueError('Unknown camera orientation')
        with self._condition:
            if self.closed:
                raise RuntimeError('Camera frame store is closed')
            if orientation != self.orientation:
                self.orientation = orientation
                self.orientation_revision += 1
                # Wake native consumers to redraw, without pretending a new camera
                # frame arrived: received/timestamp stay unchanged.
                if self._frame is not None:
                    self.sequence += 1
                self._condition.notify_all()

    def put(self, frame, source="camera"):
        if frame is None or frame.size == 0:
            return
        with self._condition:
            if self.closed:
                return
            self._frame = frame.copy()
            self.sequence += 1
            self.received += 1
            self.timestamp = time.monotonic()
            self.source = source
            self.error = None
            self._condition.notify_all()

    def read(self, max_age=3.0):
        with self._condition:
            valid = not self.closed and self._frame is not None and time.monotonic()-self.timestamp <= max_age
            return (True, orient_frame(self._frame, self.orientation)) if valid else (False, None)

    def read_new(self, after=0, timeout=1.0):
        with self._condition:
            self._condition.wait_for(lambda: self.sequence > after or self.closed, timeout)
            if self.closed or self.sequence <= after:
                return False, None, after
            return True, orient_frame(self._frame, self.orientation), self.sequence

    def status(self):
        with self._condition:
            size = [self._frame.shape[1], self._frame.shape[0]] if self._frame is not None else None
            degrees = rotation_for_shape(self._frame.shape, self.orientation) if size else 0
            output = list(reversed(size)) if size and degrees in (90, 270) else size
            return {"source": self.source, "sequence": self.sequence,
                    "orientation":self.orientation, "orientation_revision":self.orientation_revision,
                    "rotation_degrees":degrees, "input_size":size, "output_size":output,
                    "age_seconds": round(time.monotonic()-self.timestamp, 2) if self.timestamp else None,
                    "average_receive_fps": round(self.received/max(.001, time.monotonic()-self.started), 1),
                    "error": self.error}

    def isOpened(self):
        return self.read()[0]

    def clear(self):
        with self._condition:
            self._frame = None
            self.timestamp = 0
            self.source = "none"
            self.error = None

    def release(self):
        with self._condition:
            self.closed = True
            self._condition.notify_all()


class OpenCVCamera:
    """Webcam index or HTTP/MJPEG. A blocking native driver may take time to stop."""
    def __init__(self, source=0, frames=None):
        if not isinstance(source, int) and not str(source).startswith(("http://", "https://", "rtsp://")):
            raise ValueError("Camera must be a webcam index or HTTP(S)/RTSP URL, not a local file")
        self.source = source
        self.frames = frames or LatestFrame()
        self.stop_event = threading.Event()
        self.thread = None
        self.cap = None

    def start(self):
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Camera already running")
        self.thread = threading.Thread(target=self._run, daemon=True, name="camera-capture")
        self.thread.start()
        return self

    def _run(self):
        failures = 0
        while not self.stop_event.is_set():
            try:
                if isinstance(self.source, int):
                    self.cap = cv2.VideoCapture(self.source)
                else:
                    self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG,
                        [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000])
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not self.cap.isOpened():
                    raise RuntimeError("Could not open camera. Check URL, permissions and same Wi-Fi.")
                while not self.stop_event.is_set():
                    ok, frame = self.cap.read()
                    if not ok:
                        raise RuntimeError("Camera disconnected; reconnecting")
                    failures = 0
                    self.frames.put(frame, "opencv")
            except Exception as exc:
                self.frames.error = str(exc)
                failures += 1
            finally:
                if self.cap is not None:
                    self.cap.release()
            self.stop_event.wait(min(5, .5 * 2**min(failures, 4)))

    def read(self):
        return self.frames.read()

    def isOpened(self):
        return self.frames.isOpened()

    def release(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=7)
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Native camera driver is still stopping; do not open another camera yet")
        self.frames.clear()
