# Integration handoff — Member 1 and Member 2

## Recommended process boundary

Run `main.py` **once** as the camera/AI service. Member 1's PyQt GUI calls its authenticated
HTTP API from a Qt worker. This avoids Qt freezes, duplicate model instances and CUDA
contention. The web studio is a diagnostic/demo client, not a replacement requirement
for your teammate's final GUI.

Use `examples/qt_bridge.py`; install PyQt6 separately in the GUI environment.
Hold the bridge as a window member so it is not garbage-collected. Connect:

```python
self.tryon.result_ready.connect(self.show_generated_snapshot)  # BGR ndarray, dict
self.tryon.stage.connect(self.set_status_text)
self.tryon.error.connect(self.show_error)
self.tryon.submit(captured_frame, product, category=product['tryon_category'])
```

Show the original captured frame beside its generated output. Never apply a stale
snapshot to a later live camera pose. The bridge prevents multiple simultaneous GUI
submissions; service also enforces its queue bound. A native Qt direct-engine path is
possible but still must use a worker and exactly one model instance.

## Member 2: product contract

```python
{
    'image_path': r'C:\project\catalog\blue-shirt.png',  # real readable local image
    'title': 'Blue cotton shirt',
    'price': 1299.0,
    'currency': 'INR',
    'tryon_category': 'upper',  # upper | lower | overall
    'source_url': 'https://...',  # optional provenance; not passed as a local file
}
```

Retain your `search_clothes(event, budget) -> list[dict]` interface and add
`tryon_category` or let the user choose. Do not guess category from a title silently.
Use clean, centered garment-only photos where possible. Keep category/source metadata,
image rights and scraping compliance in Member 2's layer. `examples/scraper_adapter.py`
validates the local handoff. This delivery does not implement the scraper.

## Direct Python interface

```python
from tryon_engine import try_on_garment, generate_tryon
out = try_on_garment(frame, image_path, category='upper', preset='draft', seed=42)
alternatives = generate_tryon(frame, [path1, path2], category='upper')
```

- Input/output: `np.uint8`, H×W×3, **BGR**, exactly the same output dimensions.
- PIL inputs internal to the engine are **RGB**. Mask is PIL `L`; white = edit.
- Optional `mask=pil_mask` must exactly match original person geometry.
- Calls block; errors are raised, never substituted with pasted clothes.
- `generate_tryon` returns a list of independent alternatives (not stacked outfits).
- `TryOnEngine.generate(...)` returns image, mask, raw output, optional parsing and metrics.
- The singleton compatibility module is thread-safe but only serial inference is allowed.

## OpenCV-compatible camera

```python
from camera_receiver import OpenCVCamera
camera = OpenCVCamera('http://192.168.1.8:8080/video').start()
ok, frame = camera.read()  # latest fresh BGR image; never waits for inference
# Poll from a GUI timer, then copy the frame when capturing.
camera.release()
```

`LatestFrame` exposes `read`, `read_new`, `isOpened`, `release` and `status`.
It is not a full `cv2.VideoCapture` implementation: device property get/set/seek are
not provided. `isOpened()` means a fresh frame is available, not only a socket open.
WebRTC receiver writes into the same buffer; negotiation runs on an asyncio event loop.
The service handles that for HTTP clients.

## HTTP API

Every `/api/*` endpoint requires `Authorization: Bearer <terminal token>`.
Token is never placed in URLs. Browser code is same-origin. Do not add wildcard CORS
just to mask an integration issue; native Qt/Python clients don't require browser CORS.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Public basic liveness, no private images |
| GET | `/api/status` | Model-file presence, loaded state, camera info |
| POST | `/api/assets` | Multipart `file`; PNG/JPEG/WebP, max 15 MB, longest side ≤2048 |
| GET | `/api/assets/{id}` | PNG bytes; opaque validated ID only |
| POST | `/api/mask` | JSON person ID and category → mask/parsing asset IDs |
| POST | `/api/jobs` | Enqueue a captured-person/garment try-on |
| GET | `/api/jobs/{id}` | State, timestamps, error or result asset IDs/metrics |
| DELETE | `/api/jobs/{id}` | Request cancellation (active CUDA finishes safely) |
| POST | `/api/camera/open` | `{"source":"0"}` or HTTP(S)/RTSP URL |
| POST | `/api/camera/offer` | WebRTC SDP offer → SDP answer |
| POST | `/api/camera/close` | Stop/disconnect active source |
| GET | `/api/camera/frame` | JPEG monitor frame; 204 if absent/stale |
| POST | `/api/camera/capture` | Save latest full frame → person asset ID |
| DELETE | `/api/session` | Delete image assets after active work finishes |

Mask request options added in the speed/dress update: `profile="long_dress"`
(with `category="overall"`), `hem_fraction=0.92`, `flare=0.2`. The returned mask must
be reviewed, then passed to the job. Default profile is `standard`. Quality presets
now also include `dress` (576×768, 35 steps). `/api/status` and result metrics expose
`memory_mode`; staged results include phase/transfer times.

Job body:

```json
{"person":"<asset id>","garment":"<asset id>","mask":"<asset id or omit>",
 "category":"upper","preset":"draft","seed":42}
```

`mask` can be omitted to run automatic parsing inside the worker, but the studio
requires explicit mask review before generation. Empty/near-full masks are rejected.

Success: HTTP 202 and `{"id":"job id"}`. States include queued, running, loading,
masking, generating, finishing, cancelling, done, cancelled, failed. No fake percent
progress is shown because the upstream pipeline has no step callback integrated here.
Failures include 401 pairing, 400 validation, 404 expired/missing assets, 409 busy,
422 parser/request errors; generation errors appear as `state=failed` with a message.
Only a bounded in-memory job history is kept (20); restart loses job metadata but not
saved images. Images have a count/size quota. Clear the session during long demos.

## Python service client

```python
from edgeai.client import EdgeAIClient
client = EdgeAIClient('http://127.0.0.1:8000', token)
try:
    job = client.submit(captured_bgr, product['image_path'], category='upper')
    image_bgr, metrics = client.wait(job, progress=print)
finally:
    client.close()
```

Use a trusted CA certificate with HTTPS clients; do not disable TLS verification in
production. Keep the local-only HTTP loopback path for the Qt client if possible.

## Threading cautions

Qt widgets update only on the main GUI thread. Emit signals from the task. When
converting BGR→RGB→QImage, **copy QImage data** so it does not reference a freed NumPy
buffer. Do not launch multiple service processes or use uvicorn `--workers N`—each would
load its own GPU model. Do not put every preview frame into the inference queue.
