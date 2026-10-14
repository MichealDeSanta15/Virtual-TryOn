# Windows + RTX 5060 setup

## 1. Prerequisites

- 64-bit Python **3.11**, including the `py` launcher (`py -3.11 --version`).
- Current NVIDIA driver supporting your RTX 5060; verify `nvidia-smi` works.
- 16 GB RAM is a practical minimum, 32 GB preferable with CPU offload.
- Reserve about 20 GB disk for environment, model weights, cache and outputs.
- Internet for Python packages and the initial model download; no inference API key.

The CUDA runtime printed by `nvidia-smi` describes driver support. It does not tell you
which runtime is inside your PyTorch wheel. `scripts/doctor.py` reports both the
PyTorch runtime and a real CUDA matrix-multiplication test.

## 2. Install

From the extracted project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

The script creates `.venv`, installs **torch 2.7.1 / torchvision 0.22.1 cu128** and the
AI/application requirements. Do not install CatVTON's historical requirements wholesale:
its old torch/xformers pins are not suitable for this RTX 50-series target.

Manual equivalent:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements-ai.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pip check
```

A separately installed CUDA toolkit is not needed for these prebuilt wheels.
The pinned AI dependency combination is a proposed compatibility baseline; it has not
been installed or inference-tested on Windows in this workspace. Preserve the error
trace if your machine exposes a compatibility issue rather than randomly upgrading packages.

## 3. Download once

Read `LICENSES.md`, then:

```powershell
.\.venv\Scripts\python.exe scripts\download_models.py --accept-research-licenses
```

This fetches only selected files for the pinned model commits in `models.lock.json`:

- SD 1.5 inpainting UNet, scheduler, safety checker and image processor;
- CatVTON mixed-dataset attention checkpoint;
- SD VAE fine-tuned MSE;
- clothing SegFormer parser.

No Detectron2, DensePose, SCHP, SDXL or xformers build is required for the chosen path.
A successful download creates `models/manifest.json`. Downloads can take a while and
require several GB. Do not interrupt unless necessary; rerunning can reuse cached files.

## 4. Check and launch

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py --output data\my-diagnostics.json
.\.venv\Scripts\python.exe main.py
```

`doctor.py` exits 1 until all required model files and the CUDA kernel check pass.
The service itself can still run for camera/UI work without GPU dependencies.
Go to http://127.0.0.1:8000 and pair using the token printed in the terminal.

## 5. First try-on

1. Start with a front-facing, well-lit single adult. Use a narrow portrait crop that
   includes the full clothing region. The app letterboxes rather than cutting off limbs.
2. Use a clean, single-garment product photo, not a screenshot of a shop page.
3. Select the appropriate category. A top and trousers are separate alternatives,
   not one compound outfit request.
4. Create and review the edit mask. It must include the old garment and space for
   the target silhouette. Protect face, hair and overlapping hands.
5. Choose Draft, seed 42, and generate.
6. Inspect **raw output**, final image and mask. Retry a better mask before increasing
   steps blindly. Balanced/Quality can improve detail but consume more VRAM/time.

## 6. Performance settings

The latest update adds whole-model staged placement. Recommended first trial:

```powershell
$env:EDGEAI_MEMORY="staged"
.\.venv\Scripts\python.exe main.py
```

Modes: `staged` = one complete network at a time on GPU, UNet resident across all
steps; `resident` = all networks on GPU; `sequential` = original per-layer offload.
For an OOM, restart in sequential mode and choose Draft. Settings apply at process
startup. `EDGEAI_MEMORY` overrides legacy `EDGEAI_OFFLOAD`. Without either environment
variable this service defaults to staged; legacy `1` means sequential, `0` resident.

See [full speed/dress update guide](SPEED_AND_DRESSES.md) for trade-offs, benchmark
commands, monitoring and the new mask controls. No speed/VRAM guarantee is made.
Run one inference process only; close other GPU applications during benchmarking.
Runtime model access remains offline. `EDGEAI_MODELS` and `EDGEAI_DATA` override
model/data directories when set before startup.

Do not add xformers, torch.compile, LCM LoRA, quantization or TensorRT without checking
checkpoint compatibility and measuring garment fidelity. Native SDPA is already used.

## 7. Optional pose debug (not used to fake garment wrapping)

MediaPipe pose is supplementary diagnostics; CatVTON does not need pose landmarks.
For isolation from the main environment's OpenCV packages, use a separate environment:

```powershell
py -3.11 -m venv .pose-venv
.\.pose-venv\Scripts\python.exe -m pip install mediapipe==0.10.21 opencv-contrib-python==4.10.0.84 numpy==1.26.4
New-Item -ItemType Directory -Force models
Invoke-WebRequest "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task" -OutFile models\pose_landmarker_lite.task
.\.pose-venv\Scripts\python.exe scripts\pose_debug.py person.jpg
```

Review MediaPipe/model terms first. Pose-debug execution was not tested here.

## Troubleshooting

| Symptom | Action |
|---|---|
| `sm_120`, no kernel image or unsupported GPU | Ensure matched **cu128** torch/torchvision wheels, correct `.venv` and recent driver. Run doctor. |
| CUDA unavailable | Do not use CPU torch; confirm NVIDIA driver and active Python path. |
| Model not found / offline cache error | Run downloader online, then check model paths and `manifest.json`. |
| Import error after installing other ML tools | Use a clean project venv, reinstall the pinned AI stack, run `pip check`. |
| 8 GB OOM | Draft, offload=1, close GPU apps, single worker. Retry after clearing failed job. |
| OOM while loading | Verify offload=1; models are constructed on CPU. Check system RAM/page file. |
| Slow but working | CPU offload is intentionally slower. Measure before trying resident mode. |
| Output still has old sleeves/hem | Edit mask to cover old garment and target silhouette. |
| Hands disappear | Unpaint hands/forearms crossing the garment; parsing can be imperfect. |
| Dress cannot become trousers cleanly | Large category/shape changes need a manually reviewed mask; model can still fail. |
| Old outputs after restart | Images persist under data/assets. Use Delete session images. |
| Phone camera blocked | Plain LAN HTTP is insecure for getUserMedia; use trusted HTTPS or MJPEG. |
