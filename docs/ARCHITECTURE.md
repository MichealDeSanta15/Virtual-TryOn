# Architecture, realism and honest limits

**Current memory/dress update:** see [SPEED_AND_DRESSES.md](SPEED_AND_DRESSES.md).
Staged whole-model placement is now available/default absent legacy env settings,
with opt-in long-dress mask proposals and an additional Dress detail preset.
Earlier sequential-offload choices described below remain a supported fallback.

## Data flow

```text
Phone browser ── WebRTC ──┐
IP webcam ── MJPEG/RTSP ──┼─ LatestFrame (BGR, size 1, monotonic timestamp)
Laptop webcam ─ OpenCV ──┘              │
                             live preview / capture
                                       │
Catalog product image ──────────────┐   ▼
                               reviewed person snapshot + edit mask
                                   │
                   one inference worker + one pending request
                                   │
             CPU human parser (optional) → reversible letterboxing
                                   │
                   CatVTON garment-conditioned diffusion
                                   │
              restore input geometry → preserve outside-mask pixels
                                   │
                 result + raw output + mask + metrics → GUI
```

## Why a dedicated VTON model

SDXL + generic pose/segmentation ControlNets can constrain a person's structure, but do
not alone guarantee reference-garment transfer. CatVTON's learned attention uses person
and garment latent images jointly. There is no resize-and-paste garment operation in
this implementation. Letterboxing is input normalization, not garment warping onto a body.
The only final compositing blends the **generated person** with the original person
outside an approved edit region—not a product cutout.

The upstream implementation is taken from the pinned commit in `upstream.json`.
The minimal copied inference files preserve upstream licensing and attribution. Changes:
absolute imports are namespaced; a local VAE path is accepted to remove hidden runtime
model downloading. Runtime safety checking is retained.

## What "wrapped on the body" means here

It means diffusion synthesizes appearance consistent with body shape, pose, occlusion,
lighting and the garment reference. It does **not** mean 3D meshes, physical fabric
simulation, calibrated body dimensions, size selection or a guaranteed accurate fit.
CatVTON can distort garment patterns/logos, change a neckline or hem, hallucinate folds,
or fail on unusual poses. Photorealism must be judged on actual outputs.

No test photos from this user were supplied and no GPU is available in the build
workspace. Therefore there is **no claimed end-to-end generated-image validation yet**.

## Masking choices

The Windows route uses SegFormer clothing parsing on CPU rather than the official
CatVTON AutoMasker (DensePose + SCHP + Detectron2) stack. This simplifies deployment and
reduces GPU competition but is a **different mask-generation method**, not demonstrated
to match official CatVTON preprocessing quality.

Category IDs: `upper`, `lower`, `overall`. The overall mask includes dresses and the
upper/lower clothing region to support a dress replacing separates. Upper/lower-only
requests against an existing dress may require a manual mask. Arms/hands, face, hair
and shoes are protected by parsed labels; parsing can still be wrong.

Auto masks expand the detected garment boundary modestly. They do not infer the target
sleeve/hem silhouette. To change a short sleeve to a long sleeve, expand the edit mask
onto the appropriate arm but exclude the hand. For a longer hem, extend into the area
that the target garment should cover. These are reasons the editor is essential.

The final blend feathers **inside** the mask. Every pixel outside the binary mask is
copied exactly from the source photo, protecting identity/background where not painted.
A bad mask can still edit the face or create seams; protection is not face recognition.

Optional MediaPipe pose is for diagnostics only. ControlNet itself is not a pose detector;
OpenPose/MediaPipe are estimators whose outputs can condition a separate network.

## 8 GB memory and speed strategy

- Batch size one, sequential garment alternatives.
- Native PyTorch SDPA (do not overwrite learned CatVTON attention with unrelated processors).
- BF16 where supported, FP16 fallback.
- CPU construction and accelerate sequential submodule offload by default.
- VAE tiling/slicing; parser stays on CPU.
- Persistent model instance; initial model loading separated in metrics.
- Draft 384×512 / 20 steps, Balanced 512×768 / 30, Quality 768×1024 / 50.
- Model loading/UNet execution serialized by an engine lock.

More steps are not a cure for bad masks. Sequential CPU offload is intentionally
conservative, but can be much slower due to CPU↔GPU transfers. Native Windows support
for compilation/custom kernels varies; none is required here. Gradient checkpointing
is a training optimization, not the main solution for this inference-only application.
Do not add arbitrary LCM LoRA/TensorRT/quantization and promise speed without validating
checkpoint compatibility and garment fidelity.

## Metrics and concurrency

`total_seconds`: engine entry → output ready, includes cold loading on first call.
`diffusion_seconds`: conditioned model call with synchronized GPU timing.
`model_load_seconds`: original load duration, retained in later records for context.
`peak_allocated_gb`/`peak_reserved_gb`: torch CUDA allocator peaks during the request;
not the entire Windows GPU memory footprint and not a limit enforcement mechanism.
Server job timestamps additionally include queue/persistence time.

A slow GPU never consumes a backlog of every camera frame. Captures are explicit.
One pending request is accepted; another gets HTTP 409. Cancellation marks a running
job for discard after safe completion rather than interrupting CUDA mid-operation.
This can leave saved output assets on disk, which Clear session removes. Stopping the
process abruptly can terminate work; graceful GPU step-level cancellation is not built in.

## Explicitly deferred / not promised

- Real-time temporally consistent diffusion video or AR mirror rendering.
- 5 FPS inference, <2 s latency or any RTX 5060 benchmark without a measured run.
- 3D physical drape, body measurement, actual sizing or perfect garment identity.
- Guaranteed sari, layered ethnic wear, back-view or multiple-person support.
- Universal segmentation/multi-person safety; user must select a single subject.
- Automated commercial license clearance, retailer scraping, teammate GUI implementation.
- TensorRT exports, quantized checkpoints, native Android installer, desktop installer.
- Production internet hosting: authentication is a shared local pairing secret, not accounts.

## Required quality evaluation

Use at least three cases per category with consenting adults and licensed garment images:
plain top, patterned top, long sleeves; trousers, skirt, wide-leg trousers; short dress,
long dress, fitted dress. Include varying pose and body shape without treating a tiny
sample as comprehensive validation. Record source, reference, mask, raw output, final
output, seed and hardware diagnostics for each case. Score body alignment, occlusion,
identity preservation, garment similarity, seams and hallucinated features separately.
Reject misleading results rather than labeling them accurate fit predictions.
