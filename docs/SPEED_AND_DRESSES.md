# Update: GPU residency, warnings and full-dress masks

## Install the cumulative patch

1. Stop `main.py` with Ctrl+C.
2. Extract `edgeai-speed-dress-update.zip` into the EXISTING project directory that
   contains `main.py`, allowing replacement of included files.
3. Keep `.venv`, `models` and `data` untouched. No new model download or dependency
   installation is required for this update.
4. Start explicitly in the new mode:

```powershell
$env:EDGEAI_MEMORY="staged"
.\.venv\Scripts\python.exe main.py
```

Reload the browser (Ctrl+F5), pair with the new terminal token and verify that the
settings panel says **GPU MEMORY MODE · STAGED**. If not, verify that you extracted
into the correct folder and restarted the correct Python process.

This patch includes the previous constructor and meta-tensor fixes. Do not overwrite
it afterwards with one of the older patches.

## What your console screenshot means

- **Slow image processor:** describes the preprocessing implementation, not a CPU-only
  diffusion run. The update explicitly uses `use_fast=False` to match the saved parser
  behavior rather than switching preprocessing and potentially changing its output.
- **No diffusion_pytorch_model.safetensors / defaulting to unsafe serialization:** the
  initial download deliberately included the base model's `.bin` weights. Diffusers
  first tried safetensors and then loaded the available binary checkpoint. The
  completed progress bars confirm it was not fatal in these runs. The update explicitly
  selects the local format: safetensors when present, otherwise the pinned `.bin`.
  This removes the automatic fallback warning; it does NOT convert or certify pickle
  files as safe. Load only trusted downloaded model weights, not arbitrary replacements.
- **100% / 30/30 or 50/50:** normal denoising progress. The shown approximately 30–31 s
  and 112 s are loop timings, not proof of end-to-end latency or image quality.

No global warning suppression is used. Missing/corrupt weights and real errors still fail.

## Memory modes

| EDGEAI_MEMORY | Behavior | Trade-off |
|---|---|---|
| `staged` | VAE on GPU to encode; whole UNet on GPU for ALL diffusion steps; UNet moved to CPU before VAE decoding; safety checker runs separately; active model moved back to CPU on completion | Recommended first trial on your 8 GB laptop. Avoids per-layer transfers without keeping every network on GPU together. |
| `resident` | Entire pipeline stays on GPU | Avoids inter-phase transfers, but consumes more memory and may OOM. Try only after benchmarking Staged. |
| `sequential` | Original Accelerate submodule offload | Smallest GPU weight residency, but repeated CPU↔GPU transfers can dominate latency. OOM fallback. |

Examples (stop the existing service before each):

```powershell
$env:EDGEAI_MEMORY="resident"
.\.venv\Scripts\python.exe main.py

# Recovery if the faster modes exceed available memory:
$env:EDGEAI_MEMORY="sequential"
.\.venv\Scripts\python.exe main.py
```

Start with Draft or Balanced. Quality at 768×1024 can still exceed the available
VRAM because activations also need memory. No automatic silent resolution reduction
or unbounded retry is added.

`EDGEAI_MEMORY` overrides the old `EDGEAI_OFFLOAD` flag. If only the legacy flag is set,
`1` still means sequential and `0` still means resident. With neither environment
variable set, this service version defaults to staged. Direct Python
`Settings(offload=True/False)` remains backward compatible unless `memory_mode` is set.

In staged mode low VRAM use BEFORE/AFTER inference is expected. During denoising the
UNet stays resident. GPU memory occupancy is not GPU compute utilization and filling
all 8 GB is not a performance objective. CPU speed, PCIe transfers, laptop power limits,
resolution and step count also affect time.

Use NVIDIA monitoring during the progress bar rather than only Windows' default 3D graph:

```powershell
nvidia-smi --query-gpu=timestamp,name,memory.used,memory.total,utilization.gpu --format=csv -l 1
```

On Windows Task Manager, also inspect dedicated GPU memory and the CUDA/compute engine
where exposed by the driver. Some laptop/WDDM metrics may be limited.

The result panel reports the actual chosen memory mode, peak allocated VRAM and (for
staged mode) phase/weight-transfer timings. `peak_allocated_gb` is PyTorch allocation,
not the total memory shown by Windows. `weight_transfer_seconds` includes model
movement and synchronization overhead; it is not a PCIe bandwidth benchmark.

## Full dresses

The original automatic mask followed the clothes currently worn. A person in shorts
or trousers leaves a gap between the legs and may have no editable region where a long
skirt should appear. More diffusion steps cannot fix a mask that excludes the target
silhouette. However, this may not be the only cause of your dress-quality issue; an
actual input/reference/mask/output example is needed to diagnose it.

New workflow:

1. Use a front-facing **full-body** photo, including feet, with one person filling most
   of the portrait. Avoid crossed arms and heavily occluded clothing for the first test.
2. Upload a clean **complete dress** reference: do not crop off the skirt or hem.
3. Choose **Full body · dresses**.
4. For a long dress, check **Propose a long-dress edit region**.
5. Set **Hem position** to where the target dress should end on this photo. It is a
   percentage measured down the ENTIRE photo—not the person's height. 92% is only a
   starting point, not an inferred garment length.
6. Adjust **Skirt expansion**. This widens each side of the proposed skirt relative
   to the estimated waist width. It is a mask control, not a prediction of fit or drape.
7. Click **Auto mask**. The new mask fills the trouser-leg gap and permits a long/wider
   skirt while protecting parsed face, hair, arms/hands and shoes.
8. Review and paint/erase as needed. If sleeves should extend onto exposed arms, paint
   those regions manually while preserving hands. Shoes are protected automatically;
   for a floor-length gown covering shoes, manually review/extend that region.
9. Try **Dress detail · 576×768 / 35 steps**. It has the training canvas's 3:4 aspect
   ratio at a moderate resolution. This is an additional option, not a promise that
   it beats all other presets. For maximum detail try Quality only after checking VRAM.

Changing dress-mask controls clears the previous editor mask. Click Auto mask again.
The parser caches ONLY the latest label map in RAM so adjusting hem/width need not
rerun the neural parser for the same image; Clear session also clears that cache.

For short dresses or fitted looks, Standard plus manual editing may work better than
an expanded mask. A large edit area gives the model more freedom to change details.
The new long-dress mask is a geometrical edit-region proposal—not 3D cloth simulation,
a segmentation of the target garment, or learned garment-identity improvement.
The model and its trained weights are unchanged. Patterns, logos, fabric properties,
exact silhouette and layered ethnic wear can still be inaccurate.

## Compare fairly

To isolate speed, compare sequential vs staged using the SAME person, garment,
reviewed mask, seed, resolution and step count. Do one cold and at least two warm
requests per mode. Don't compare 50-step Quality to 20-step Draft and credit the mode.

```powershell
# Stop main.py first. Use a mask with EXACTLY the person image's dimensions.
$env:EDGEAI_MEMORY="sequential"
.\.venv\Scripts\python.exe scripts\tryon.py --person person.png --garment dress.png --mask mask.png --category overall --preset balanced --runs 3 --output data\bench-sequential
$env:EDGEAI_MEMORY="staged"
.\.venv\Scripts\python.exe scripts\tryon.py --person person.png --garment dress.png --mask mask.png --category overall --preset balanced --runs 3 --output data\bench-staged
```

CLI automatic masking remains Standard unless a reviewed mask is supplied. The browser
may downsize uploads to 1600px; use a matching person image if exporting a browser mask.

For quality, compare original/reference/mask/raw/final images, not only latency. Send
a failing example (with subject consent) for a targeted follow-up. No visual dress
accuracy or RTX 5060 speed improvement has been measured in this build workspace.

## Verification for this update

- Full automated suite: 44 tests pass.
- Real tiny random-weight CatVTON execution, repeated twice, passes in sequential,
  staged and resident modes on CPU. Production weights/RTX 5060 not tested here.
- Staged eviction order and retention between denoising calls checked.
- Long-dress extent, gap filling, protected face/hands/shoes and parameter checks pass.
- Local format selection prefers safetensors and selects existing .bin explicitly;
  a small saved Diffusers .bin checkpoint was loaded successfully using that path.
- Browser pairing, displayed Staged mode, dress controls/ranges/preset, category
  switching and mobile width tested in Chromium with no JavaScript errors.
- Python compile and JavaScript syntax checks pass.

The CPU tests establish code execution and invariants, not model quality or GPU speed.
