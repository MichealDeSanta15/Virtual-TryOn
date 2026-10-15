# FORM — EdgeAI virtual try-on

**Member 3 delivery: phone camera, diffusion try-on, optimization and integration.**
Target: **Windows · RTX 5060 8 GB · academic/non-commercial use**.

**Portrait camera update:** [Phone orientation, preview and capture](docs/CAMERA_ORIENTATION.md).
Rotate the actual camera pixels consistently for the monitor and captured person image;
already-portrait frames are not double-rotated by the portrait modes.

**Garment / dress update:** [Garment-only reference preparation and sleeve masks](docs/GARMENT_AND_DRESS_FIX.md).
Selecting/uploading a model-worn reference now extracts clothing on CPU, offers a keep/erase
editor and requires review before studio generation. No new weights required.

**Free live catalog update:** [Install the live-first scraper](docs/LIVE_CATALOG.md).
Fresh public-feed searches from No Nasties, Femmella, Nobero and The Summer House;
real garment photos feed into the existing try-on flow. No API key or paid provider.
Run `scripts/setup_catalog.ps1`; no GPU/model reinstallation or Chromium needed for
the default stores. Live failures never silently return saved products.
[Full catalog/API guide](docs/CATALOG_INTEGRATION.md).

**GPU/dress update:** [GPU residency and dress-mask controls](docs/SPEED_AND_DRESSES.md).
Use `$env:EDGEAI_MEMORY="staged"` before startup for whole-model phase offload;
this takes precedence over the older `EDGEAI_OFFLOAD` flag. New long-dress mask
controls and a 576×768/35-step Dress detail preset are available.

> This is an implemented research prototype, not a verified real-time clothing simulator.
> The CPU/API/WebRTC tests run here; GPU inference, Windows installation, physical phone
> pairing and visual realism still require validation on your machine. No fabricated
> try-on images or synthetic performance claims are included.

## What is included

- A browser phone publisher and **aiortc WebRTC receiver**, with no public STUN/TURN.
- OpenCV laptop-webcam / HTTP-MJPEG / RTSP input, reconnect logic and latest-frame buffer.
- **CatVTON** garment-conditioned diffusion, using a local SD 1.5 inpainting base and
  dedicated learned try-on attention weights—not product-image pasting.
- Upper-body, lower-body and overall/dress requests, processed one garment at a time.
- CPU SegFormer clothing parser, reviewable masks, paint/erase editor and manual fallback.
- Original geometry restored; pixels outside the approved edit mask preserved exactly.
- Mixed precision, native PyTorch SDPA, VAE tiling/slicing, CPU offload and persistent model reuse.
- A single inference worker, bounded pending queue, explicit errors/cancellation, timings/VRAM.
- A local studio UI for testing. Your teammate's PyQt6 UI can use the same backend.
- Static-image runner, benchmark runner, Windows setup, GPU doctor, optional pose debugging.
- Member 1/2 integration contracts, Python/HTTP clients, PyQt signals bridge and tests.

## Start on Windows

Install **Python 3.11 (64-bit)** and a recent NVIDIA driver first. Extract this project;
open PowerShell **in the project folder**. Recommended practical starting resources:
16 GB system RAM minimum (32 GB preferable for CPU offload) and 20 GB free disk.
These are planning allowances, not measured peak requirements.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

Read [model licenses](docs/LICENSES.md), then download the pinned snapshots once:

```powershell
.\.venv\Scripts\python.exe scripts\download_models.py --accept-research-licenses
.\.venv\Scripts\python.exe scripts\doctor.py --output data\my-diagnostics.json
.\.venv\Scripts\python.exe main.py
```

Open **http://127.0.0.1:8000**. Click **Pair browser** and paste the terminal token.
Upload a person photo and a clean garment image, choose the category, generate an
**Auto mask**, review/edit it, and run **Draft** first. Initial model loading can take time.
The process stays alive to reuse weights across requests.

If automatic masking is unsuitable, paint the mask manually. No GPU/weights means
an explicit error—there is deliberately no convincing-looking fake fallback.

### First real GPU validation

```powershell
.\.venv\Scripts\python.exe scripts\tryon.py --person person.jpg --garment shirt.jpg --category upper --preset draft --runs 3 --output data\first-test
```

Inspect `result-1.png`, `raw-1.png`, `mask-1.png` and `benchmark.json`.
Use your own consenting subject and a garment photo you are permitted to use.

## Phone camera

**Fastest route:** IP Webcam/DroidCam on your phone → same Wi-Fi → enter its actual
MJPEG endpoint in the Camera tab, e.g. `http://192.168.1.8:8080/video`. Or use a webcam
index such as `0`. DroidCam's virtual webcam may appear as another index.

**Browser/WebRTC route:** host with a trusted HTTPS certificate and open
`https://YOUR-LAPTOP-IP:8000/phone` on the phone. A plain HTTP LAN URL does not grant
browser camera access. See [phone setup](docs/PHONE_CAMERA.md).

## Teammate interfaces

```python
from tryon_engine import try_on_garment

# BGR uint8 NumPy frame in, same-sized BGR frame out. This call BLOCKS.
# Run it on a worker, never in Qt's UI event loop.
result = try_on_garment(frame, product["image_path"], category="upper", preset="draft")
```

`generate_tryon(frame, garment_paths)` returns **a list of independent alternatives**.
Use [the integration guide](docs/INTEGRATION.md) for the HTTP client and Qt bridge.
The repaired Member 2 catalog is now integrated. See its guide for live-site limitations; this project does not bypass retailer restrictions.

## Why this differs from your original plan

Generic SDXL + pose ControlNet does not by itself transfer a selected garment's identity.
CatVTON is specifically trained for image-conditioned try-on. It models appearance of
folds, occlusion and body alignment through diffusion. It is **not** explicit 3D cloth
physics, does not know fabric stretch/size, and cannot guarantee exact logos or fit.

We separate live camera preview from generated stills. We do **not** attach an old
result to a newly moving body or call camera throughput "try-on FPS". Five realistic
new diffusion results per second and <2 s latency on this GPU remain unproven.
See [architecture and limitations](docs/ARCHITECTURE.md).

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

See [verification report](docs/VERIFICATION.md) for precisely what was and was not tested.
The test-only engine double exists exclusively under `tests/`, never in the application.

## Project map

```text
main.py                     local service entry point
camera_receiver.py          compatible camera imports
tryon_engine.py             direct Python integration API
edgeai/camera.py             thread-safe latest frame + OpenCV reconnect
edgeai/webrtc.py             WebRTC video receiver
edgeai/engine.py             actual CatVTON inference and postprocessing
edgeai/masking.py            category-aware parsing + protected regions
edgeai/imaging.py            reversible geometry and exact outside-mask preservation
edgeai/worker.py             one active / one pending job and status
edgeai/server.py             authenticated local HTTP API
edgeai/client.py             teammate HTTP client
edgeai/web/                  testing studio + phone publisher
edgeai/vendor/catvton/       minimal attributed upstream inference implementation
examples/                   Qt bridge, scraper contract, direct API example
scripts/                    Windows setup, model download, doctor, benchmark, pose
models.lock.json            pinned model revisions and selected files
```

## Privacy / licensing

Inference is offline after setup; neither images nor prompts are sent to an AI API.
Images uploaded/captured/generated by the service are saved under `data/assets/`.
Use **Delete session images** to remove them. Benchmark outputs are separate and must
be removed separately. No auto-deletion after generation; do not assume it is ephemeral.
Camera preview frames remain in RAM until a snapshot is taken. The hosted preview is
not your laptop: use non-sensitive test images there and run locally for private photos.

Bind to localhost unless phone access is needed. For LAN access, use trusted Wi-Fi,
HTTPS, a fresh random pairing token and a Windows Private-network firewall rule.
Do not internet-expose this research server. The token grants full studio access.

The original team scraper code has no confirmed license grant in the reviewed branch;
see `docs/catalog/AUDIT.md` before redistributing it. Academic/non-commercial
distribution under **CC BY-NC-SA 4.0** for the previously supplied integration
and upstream CatVTON portions; other dependencies/weights retain their own licenses.
See [attribution and model terms](docs/LICENSES.md).
