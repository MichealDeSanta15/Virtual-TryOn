# Cumulative fix: Accelerate / VAE meta-tensor error

## Apply on Windows

1. Stop main.py completely using Ctrl+C. Also close any notebook/kernel or other
   application that imported the previous pipeline.
2. Extract `edgeai-offload-fix.zip` into your EXISTING project root (contains main.py).
   Allow overwriting the included source files. Do not extract into the edgeai
   subfolder or another nested project folder.
3. Leave `.venv`, `models` and `data` in place. No model downloads or package upgrades.
4. From the same project folder run:

```powershell
# Optional: runs small actual-model CPU/offload regression tests, with no downloads.
.\.venv\Scripts\python.exe -m pytest -q tests/test_offload_runtime.py tests/test_pipeline_contract.py

# Keep the 8 GB GPU memory-saving mode enabled, then start a fresh process.
$env:EDGEAI_OFFLOAD="1"
.\.venv\Scripts\python.exe main.py
```

Pair the browser using the new terminal token, then retry Draft.
If an error remains, copy the FULL traceback from the terminal, not only the UI's
one-line summary. This patch adds terminal traceback logging to job failures.

This patch includes the earlier vae_ckpt constructor fix. Apply this cumulative patch
last; there is no need to apply the older patch afterwards.

## Root cause reproduced

Accelerate's sequential cpu_offload keeps idle module parameters on the `meta`
device while retaining their real values separately. `vae.device` therefore does
not reliably identify where inputs should execute. The previous helper did:

```python
pixel_values = pixel_values.to(vae.device, dtype=vae.dtype)
```

This moved real image data to meta. On the next encode operation, Accelerate tried
to transfer that now-data-less input to the execution device and raised:

    NotImplementedError: Cannot copy out of meta tensor; no data!

The corrected helper takes the pipeline's execution device explicitly and moves
images only to that real device, retaining the VAE dtype. Parameters may still be
meta between calls; that is expected. Offloading remains enabled. Do not substitute
`to_empty()` for this fix: it allocates storage, not the lost image/weight values.

## Verification actually performed

- Reproduced the identical exception using the original transfer pattern with a
  real, tiny Diffusers AutoencoderKL and actual Accelerate cpu_offload hooks.
- Corrected helper passes repeated encode/decode cycles and retains meta parameter
  storage between calls (offloading is not silently disabled).
- Corrected offloaded encoder agrees with the resident CPU encoder for identical
  weights, input and random seed.
- Tiny random-weight CatVTON execution path passes two successive generation calls:
  encode -> CFG UNet -> scheduler -> decode, with both UNet and VAE offloaded.
- Both standard and Pix2Pix pipeline callers explicitly pass their execution device.
- Prior vae_ckpt constructor-contract tests still pass.
- Full suite: **32 passed**, one TestClient dependency deprecation warning.

Environment: Linux, Python 3.13.16, torch 2.7.1+cpu, diffusers 0.31.0,
accelerate 1.6.0, transformers 4.48.3. No CUDA GPU in this workspace.
The targeted tests use tiny randomly initialized models, not trained garment
weights, and do NOT establish photorealism, VRAM use or RTX 5060 performance.
The tiny-pipeline test bypasses pretrained loading and safety checking only inside
its test harness. Production model loading and safety checking remain unchanged.
