import asyncio
import hmac
import importlib.util
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import cv2
from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, Response, JSONResponse
from pydantic import BaseModel, Field

from .config import Settings, CATEGORIES
from .camera import LatestFrame, OpenCVCamera
from .webrtc import WebRTCReceiver
from .engine import TryOnEngine
from .imaging import load_rgb, bgr_to_pil
from .storage import Storage
from .worker import TryOnWorker, BusyError

WEB = Path(__file__).parent / "web"


class CatalogRequest(BaseModel):
    event: str = Field(min_length=1,max_length=160)
    budget: str = Field(default="5000",max_length=60)
    brand: str | None = Field(default=None,max_length=80)
    category: str | None = Field(default=None,max_length=40)
    color: str | None = Field(default=None,max_length=40)
    source: Literal["nonasties","femella","nobero","summerhouse","myntra","ajio","amazon","local"] | None = None
    live: bool = True
    refresh: bool = False
    limit: int = Field(default=24,ge=1,le=50)


class GarmentPrepareRequest(BaseModel):
    garment: str
    category: Literal["upper", "lower", "overall"] = "upper"
    mask: str | None = None  # original reference-photo geometry, NOT person mask


class GenerateRequest(BaseModel):
    person: str
    garment: str
    preparation: str | None = None
    garment_reviewed: bool = False
    mask: str | None = None
    category: Literal["upper", "lower", "overall"] = "upper"
    preset: Literal["draft", "balanced", "quality", "dress"] = "draft"
    seed: int = Field(default=42, ge=0, lt=2**32)


class MaskRequest(BaseModel):
    person: str
    category: Literal["upper", "lower", "overall"] = "upper"
    profile: Literal["standard", "long_dress"] = "standard"
    hem_fraction: float = Field(default=.92, ge=.5, le=.98)
    flare: float = Field(default=.2, ge=0, le=.6)
    sleeves: bool = False


<<<<<<< HEAD
CameraOrientation = Literal["source", "portrait_cw", "portrait_ccw", "cw90", "ccw90", "180"]


class CameraRequest(BaseModel):
    source: str = Field(default="0", max_length=512)
    orientation: CameraOrientation | None = None


class CameraOrientationRequest(BaseModel):
    orientation: CameraOrientation
=======
class CameraRequest(BaseModel):
    source: str = Field(default="0", max_length=512)
>>>>>>> origin/main


class OfferRequest(BaseModel):
    sdp: str = Field(max_length=100_000)
    type: Literal["offer"]


def create_app(settings=None, token=None, engine=None):
    settings = settings or Settings.from_env()
    token = token or os.environ.get("EDGEAI_TOKEN")
    if not token or len(token) < 16:
        raise ValueError("Set EDGEAI_TOKEN to a random string of at least 16 characters")
    engine = engine or TryOnEngine(settings)
    store = Storage(settings.data_dir / "assets", settings.max_upload_mb)
    frames = LatestFrame()
    receiver = WebRTCReceiver(frames)
    camera = None
    worker = None
    catalog_worker = None
    garment_worker = None
    from .catalog import CatalogService
    catalog = CatalogService(settings, store)
    mask_busy = asyncio.Lock()

    def run_prepare(progress, garment, category, mask=None):
        source = load_rgb(store.path(garment))
        selection = load_rgb(store.path(mask)).convert('L') if mask else None
        prepared = engine.prepare_garment(source, category, mask=selection, progress=progress)
        return {'garment':store.save(prepared.image), 'mask':store.save(prepared.mask),
                'source':garment, 'category':category, 'metadata':prepared.metadata}

    def run_job(progress, **req):
        preparation = req.pop('preparation', None)
        reviewed = req.pop('garment_reviewed', False)
        person = load_rgb(store.path(req.pop("person")))
        garment = load_rgb(store.path(req.pop("garment")))
        mask_key = req.pop("mask", None)
        mask = load_rgb(store.path(mask_key)).convert("L") if mask_key else None
        result = engine.generate(person, garment, mask=mask, progress=progress, **req)
        return {"image": store.save(result.image), "mask": store.save(result.mask),
                "raw": store.save(result.raw), "metrics": result.metrics,
                "parsing": store.save(result.parsing) if result.parsing else None,
                "condition": store.save(result.condition) if getattr(result, "condition", None) else None,
                "preparation":preparation, "garment_reviewed":reviewed}

    @asynccontextmanager
    async def lifespan(app):
        nonlocal worker, camera, catalog_worker, garment_worker
        worker = TryOnWorker(run_job)
        app.state.worker = worker
        catalog_worker = TryOnWorker(catalog.search, history=12)
        app.state.catalog_worker = catalog_worker
        app.state.catalog = catalog
        garment_worker = TryOnWorker(run_prepare, history=12)
        app.state.garment_worker = garment_worker
        yield
        await receiver.close()
        if camera:
            try:
                await asyncio.to_thread(camera.release)
            except RuntimeError:
                pass
        worker.close()
        catalog_worker.close()
        garment_worker.close()
        frames.release()

    app = FastAPI(title="EdgeAI Try-On • local research prototype", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.frames = frames

    async def authorized(request: Request):
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
        # Never put a token in a URL, logs, referer or an image src.
        if not hmac.compare_digest(supplied, token):
            raise HTTPException(401, "Pair this browser using the token printed in your terminal")

    auth = [Depends(authorized)]

    @app.middleware("http")
    async def security_headers(request, call_next):
        # Streaming endpoints also enforce actual size while reading, not only Content-Length.
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > (settings.max_upload_mb + 1)*1024**2):
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # No CORS: use the same-origin UI, or a trusted native client with a bearer token.
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.get("/")
    async def index():
        return FileResponse(WEB / "index.html")

    @app.get("/phone")
    async def phone():
        return FileResponse(WEB / "phone.html")

    @app.get("/static/{name}")
    async def static(name: str):
        if name not in ("app.js", "garment.js", "style.css"):
            raise HTTPException(404)
        return FileResponse(WEB / name)

    @app.get("/health")
    async def health():
        return {"service": "edgeai-tryon", "version": "0.1.0", "mode": "real-model-only"}

    @app.get("/api/status", dependencies=auth)
    async def status():
        return {"models_present": all((settings.model_dir/p).exists() for p in ("base", "catvton", "parser", "vae")),
                "torch_installed": importlib.util.find_spec("torch") is not None,
                "pipeline_loaded": engine.pipeline is not None,
                "camera": frames.status(), "offline": settings.offline,
                "offload": settings.effective_memory_mode != "resident",
                "memory_mode": settings.effective_memory_mode, "categories": CATEGORIES}

    @app.post("/api/catalog/search", dependencies=auth, status_code=202)
    async def catalog_search(req: CatalogRequest):
        from clothing_pipeline.search.engine import SearchEngine
        SearchEngine.parse_budget(req.budget)  # Reject invalid filters before starting work.
        if not req.event.strip(): raise HTTPException(400, "Enter an occasion or garment")
        values = req.model_dump()
        values['scrape_if_empty'] = values.pop('live')
        try:
            return {"id":catalog_worker.submit(**values)}
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/catalog/search/{job_id}", dependencies=auth)
    async def catalog_search_status(job_id: str):
        try: return catalog_worker.get(job_id)
        except KeyError: raise HTTPException(404,"Unknown or expired catalog search")

    @app.get("/api/catalog/products/{product_id}/image", dependencies=auth)
    async def product_image(product_id: int):
        path = await asyncio.to_thread(catalog.image_path, product_id)
        def thumbnail():
            from io import BytesIO
            image = load_rgb(path)
            image.thumbnail((480,640))
            buffer = BytesIO();image.save(buffer,format="PNG")
            return buffer.getvalue()
        return Response(await asyncio.to_thread(thumbnail), media_type="image/png")

    @app.post("/api/catalog/products/{product_id}/select", dependencies=auth)
    async def select_product(product_id: int):
        return await asyncio.to_thread(catalog.select, product_id)

    @app.post("/api/assets", dependencies=auth)
    async def upload(file: UploadFile = File(...), mask: bool = False):
        try:
            data = await file.read(store.max_bytes + 1)
            key = await asyncio.to_thread(store.upload, data, mask)
        finally:
            await file.close()
        return {"id": key}

    @app.get("/api/assets/{key}", dependencies=auth)
    async def asset(key: str):
        return FileResponse(store.path(key), media_type="image/png")

    @app.post("/api/garments/prepare", dependencies=auth, status_code=202)
    async def prepare_garment(req: GarmentPrepareRequest):
        store.path(req.garment)
        if req.mask: store.path(req.mask)
        try:
            return {"id":garment_worker.submit(**req.model_dump())}
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/garments/prepare/{job_id}", dependencies=auth)
    async def garment_preparation(job_id: str):
        try: return garment_worker.get(job_id)
        except KeyError: raise HTTPException(404, "Unknown/expired garment preparation")

    @app.post("/api/mask", dependencies=auth)
    async def mask(req: MaskRequest):
        if mask_busy.locked():
            raise HTTPException(409, "Mask parser is busy")
        async with mask_busy:
            person = load_rgb(store.path(req.person))
            try:
                mask, parsing = await asyncio.to_thread(engine.make_mask, person, req.category,
                                                          profile=req.profile, hem_fraction=req.hem_fraction, flare=req.flare, sleeves=req.sleeves)
            except Exception as exc:
                raise HTTPException(422, f"Automatic masking unavailable: {exc}. Paint a manual mask instead.") from exc
            return {"mask": store.save(mask), "parsing": store.save(parsing)}

    @app.post("/api/jobs", dependencies=auth, status_code=202)
    async def submit(req: GenerateRequest):
        for key in (req.person, req.garment, req.mask):
            if key:
                store.path(key)
        if req.garment_reviewed and not req.preparation:
            raise HTTPException(400, 'Reviewed references require a preparation ID.')
        if req.preparation:
            try: prepared = garment_worker.get(req.preparation)
            except KeyError: raise HTTPException(409, 'Garment preparation expired. Extract and review again.')
            r = prepared.get('result') or {}
            if prepared['state'] != 'done' or r.get('garment') != req.garment or r.get('category') != req.category:
                raise HTTPException(409, 'Prepared garment/category mismatch. Extract the current reference again.')
            if not req.garment_reviewed:
                raise HTTPException(400, 'Review the garment-only preview before generating.')
        try:
            return {"id": worker.submit(**req.model_dump())}
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/jobs/{job_id}", dependencies=auth)
    async def job(job_id: str):
        try:
            return worker.get(job_id)
        except KeyError:
            raise HTTPException(404, "Unknown/expired job")

    @app.delete("/api/jobs/{job_id}", dependencies=auth)
    async def cancel(job_id: str):
        try:
            worker.cancel(job_id)
            return {"status": "cancellation requested; active CUDA work finishes safely"}
        except KeyError:
            raise HTTPException(404, "Unknown/expired job")

    @app.post("/api/camera/open", dependencies=auth)
    async def camera_open(req: CameraRequest):
        nonlocal camera
        await receiver.close()
        if camera:
            await asyncio.to_thread(camera.release)
        source = int(req.source) if req.source.isdigit() else req.source
<<<<<<< HEAD
        if req.orientation is not None:
            frames.set_orientation(req.orientation)
        camera = OpenCVCamera(source, frames).start()
        return {"status": "opening"}

    @app.post("/api/camera/orientation", dependencies=auth)
    async def camera_orientation(req: CameraOrientationRequest):
        # Shared by preview and saved capture; never a browser-only CSS transform.
        frames.set_orientation(req.orientation)
        return frames.status()

=======
        camera = OpenCVCamera(source, frames).start()
        return {"status": "opening"}

>>>>>>> origin/main
    @app.post("/api/camera/offer", dependencies=auth)
    async def offer(req: OfferRequest):
        nonlocal camera
        if camera:
            await asyncio.to_thread(camera.release)
            camera = None
        return await receiver.offer(req.sdp, req.type)

    @app.post("/api/camera/close", dependencies=auth)
    async def camera_close():
        nonlocal camera
        await receiver.close()
        if camera:
            await asyncio.to_thread(camera.release)
            camera = None
        frames.clear()
        return {"status": "closed"}

    @app.get("/api/camera/frame", dependencies=auth)
    async def camera_frame():
        ok, frame = frames.read()
        if not ok:
            return Response(status_code=204)
<<<<<<< HEAD
        # Orient first (LatestFrame.read), then bound BOTH portrait/landscape preview.
        # Capture retains the full oriented image, subject to its normal 2048px limit.
        h, w = frame.shape[:2]
        if max(w, h) > 800:
            scale = 800 / max(w, h)
            frame = cv2.resize(frame, (max(1, round(w*scale)), max(1, round(h*scale))))
=======
        # Small monitor preview; original captured frame is retained separately.
        h, w = frame.shape[:2]
        if w > 800:
            frame = cv2.resize(frame, (800, round(h*800/w)))
>>>>>>> origin/main
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ok:
            raise HTTPException(500, "JPEG encode failed")
        return Response(buf.tobytes(), media_type="image/jpeg")

    @app.post("/api/camera/capture", dependencies=auth)
    async def capture():
        ok, frame = frames.read()
        if not ok:
            raise HTTPException(409, "No fresh camera frame. Pair a phone or open a webcam.")
        image = bgr_to_pil(frame)
        image.thumbnail((2048, 2048))
<<<<<<< HEAD
        return {"id": store.save(image), "width":image.width, "height":image.height}
=======
        return {"id": store.save(image)}
>>>>>>> origin/main

    @app.delete("/api/session", dependencies=auth)
    async def clear_session():
        with worker.lock, garment_worker.lock:
            if (any(j.finished is None for j in worker.jobs.values()) or
                    any(j.finished is None for j in garment_worker.jobs.values()) or mask_busy.locked()):
                raise HTTPException(409, "Wait for jobs/masking to finish before clearing files")
            store.clear()
            worker.jobs.clear()
            garment_worker.jobs.clear()
            parser = getattr(engine, "parser", None)
            if parser is not None:
                parser.clear_cache()
        return {"status": "All session images deleted"}

    return app
