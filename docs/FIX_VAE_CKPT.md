# Fix: unexpected keyword argument vae_ckpt

Cause: the engine passed vae_ckpt and the VAE loader referenced it, but the bundled
CatVTONPipeline.__init__ signature did not declare the parameter. This was a delivery
bug, not a CUDA, dependency or model-download problem.

## Apply to your existing project

1. Stop main.py with Ctrl+C. Close any other process that imported the pipeline.
2. Extract this patch into your EXISTING project root (the folder with main.py).
3. Allow replacement of edgeai/vendor/catvton/model/pipeline.py.
   The patch also includes tests/test_pipeline_contract.py and this note.
4. Do not remove your .venv, models or data folders; no reinstallation is required.
5. Optional regression check:
   .\.venv\Scripts\python.exe -m pytest -q tests/test_pipeline_contract.py
6. Restart:
   .\.venv\Scripts\python.exe main.py
7. Retry the same Draft try-on.

Manual equivalent: inside CatVTONPipeline.__init__, append the following parameter
after use_tf32=True and before the closing parenthesis:

    vae_ckpt="stabilityai/sd-vae-ft-mse",

Keep the engine's vae_ckpt argument and the VAE loader's from_pretrained(vae_ckpt).
The engine supplies your local models/vae path; the default preserves compatibility
with upstream callers.

Verification: two new source-contract tests pass; full CPU/integration suite is now
24 passed. No actual GPU inference was performed in the build workspace. Your supplied
diagnostics report successful CUDA execution and all expected model files present;
this patch resolves the constructor mismatch, not a certification of image quality.
