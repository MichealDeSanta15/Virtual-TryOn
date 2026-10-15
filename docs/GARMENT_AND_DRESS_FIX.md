# Garment-only references and dress-mask update

**15 October 2026 · existing Windows / RTX 5060 8 GB studio**

Your screenshot shows failed garment transfer: the output retains a green sleeveless
silhouette rather than the brown, collared, sleeved reference dress. This update
addresses verified input/mask problems. It is **not** proof that CatVTON now reproduces
the dress accurately; that requires another GPU run on your laptop.

## Install

1. Stop the server (Ctrl+C). Back up local code edits.
2. Extract **edgeai-garment-dress-fix.zip** into the existing project folder containing
   `main.py`, replacing files. This patch is for the current live-catalog project.
   Keep `.venv`, models and data; do not delete or reinstall the working GPU stack.
3. Restart:

```powershell
$env:EDGEAI_MEMORY="staged"
.\.venv\Scripts\python.exe main.py
```

4. Ctrl+F5 in the browser, then pair again. Existing selections must be reselected and
   extracted. If the new review checkbox is absent, the browser/source update is stale.

**No new model or dependency is required on your already-configured laptop.** The
existing local SegFormer clothes parser runs on CPU; the screenshot's model-readiness
report indicated those weights are installed. If they are missing, use the existing
model downloader. There is no image upload to a remote AI or scraping provider.

The full-source alternative is **edgeai-garment-dress-project.zip**. It includes the
live scraper and this update, not weights, `.venv`, user photos or prefetched products.

## What is different

### Clothing extraction, not just background removal

Previously the selected catalog image—including its model and setting—was passed
straight to the garment-conditioning input. Now selecting a product or uploading a
reference automatically starts **CPU clothing segmentation**:

- Keep the requested clothing category and adjacent belt; exclude face, hair, skin,
  arms/hands, legs, shoes, background and unrelated accessories according to labels.
- For dresses, preserve clothing-labelled inner panels/ties even when the parser calls
  those pixels upper clothing instead of dress. Never blindly fill a hand/skin hole.
- Crop to the clothing, preserve aspect ratio, add a white margin and retain observed
  garment colours. This does not flatten the garment or reconstruct hidden fabric.
- Keep the original photo separately for correction. It is not the studio's ready
  garment asset. `garmentId` stays unset until preparation succeeds.
- No original-model-photo fallback if extraction fails. A visible error directs you
  to a manual garment-selection mask or a better reference photo.

The garment panel shows the **extracted reference**. Open **Review / correct reference
selection** to paint missing cloth or erase retained skin/background. Green shows
pixels to KEEP. Apply corrected selection, then inspect the new cutout. Automatic
segmentation can still be wrong: review is mandatory, not a claim of perfect detection.

Check **I reviewed the garment-only preview** only after inspection. Any reference,
category or mask change invalidates the prepared asset/review. The studio cannot send
its generation request until a valid reviewed preparation exists. The backend checks
that the preparation ID, prepared asset and category match.

### Why sleeveless-to-sleeved transfer was constrained

The previous automatic person mask protected *all* exposed arms. Outside-mask pixels
are intentionally copied exactly from the original, so more inference steps cannot
add sleeves to arm pixels that remain protected.

There is now an opt-in **Allow short sleeves on upper arms (review hands)** proposal.
It allows edits on the proximal portion of segmented arms, while retaining distal-arm,
face/hair/shoe protections. It is a geometry heuristic, not a hand or pose detector.
Bent, raised or occluded arms can be misinterpreted: inspect and manually correct the
person mask, especially overlapping hands. The default remains conservative/off.

Full-dress selection also switches Draft/Balanced to **Dress detail · 576×768 / 35
steps**. This is a useful starting preset, not a promised quality improvement or a
new GPU benchmark. An explicitly selected Quality preset is not overwritten.

### Debugging actual conditioning

Completed generation results now include **Actual garment input**, the prepared and
letterboxed reference given to the diffusion pipeline. Download it alongside **Download
mask** and **Raw model output**. Metrics include guidance scale and mask coverage.
The static try-on runner also saves `condition-N.png`.

True transparent uploads are composited onto white rather than dropping alpha into
black. A checkerboard baked into the image pixels is not transparency and is not
silently removed. Prefer the original clean person photo, not a screenshot.

## Retry the exact example

1. Select the brown dress again, category **Full body · dresses**.
2. Wait for the white-background, clothing-only preview. Verify collar, sleeves, belt,
   skirt and hem; correct any gaps/skin with the reference selection editor. Confirm.
3. Choose **Dress detail**. Keep the same seed for a controlled comparison.
4. On the PERSON mask, enable the short-sleeve proposal, click Auto mask, then inspect.
   Cover all the old green garment plus space needed for the new shoulders/sleeves,
   waist tie and hem. Keep face, hair, hands and shoes out of the white edit region.
5. Do **not** automatically enable the long-dress envelope for this short dress. That
   control deliberately extends the editable skirt towards the bottom of the photo.
6. Generate. Compare the result to the brown reference—not merely whether it completed.

The reference is photographed with one arm extended, asymmetric folds and some
occlusion. Removing the wearer does not turn it into a clean flat-lay or recover
unseen sleeves/fabric. A complete, front-facing product image is still preferable.

If it remains green, keep the actual downloaded files, not only screenshots:

- Actual garment input (should show the brown extracted garment).
- Person mask (white should cover old dress and intended new silhouette).
- Raw model output, final result and metrics.

If the raw model image transfers the garment but the final result does not, inspect
mask/compositing coverage. If the raw image also fails despite the correct condition
and mask, investigate model/conditioning fidelity rather than blindly increasing
steps. This model is not a guaranteed exact colour/pattern/shape-transfer system.

## What was tested

- **131 automated tests passed**; one existing Starlette/httpx deprecation warning.
- New deterministic tests: category-only extraction, exclusion of body pixels,
  belt/inner clothing panels, preserving skin/background holes, crop/colour contract,
  invalid masks, alpha-to-white, sleeve protections and API review/category binding.
- The actual pinned SegFormer model ran on CPU on the brown reference cropped from
  your screenshot. Its final clothing mask retained about **44.04%** of that crop;
  the extracted reference visibly removed the model and setting. This is not a
  generated try-on image or an accuracy percentage.
- Actual browser upload → learned extraction → preview → review gate → real CPU person
  mask with sleeve option; manual reference painting/apply invalidated/recreated the
  preparation. Desktop/mobile layouts and JS-error checks passed.
- Actual selection of a previously downloaded real Femmella dress triggered extraction,
  produced a separate prepared asset, required review and invalidated on category change.
  This check reused saved real products; it did not re-test live retailer availability.
- Python compileall and both JavaScript syntax checks passed.

**Not tested:** learned diffusion on the RTX 5060, Windows script execution, resulting
dress realism/colour fidelity, or quality across arbitrary model poses. Existing
staged-memory fixes and real diffusion engine were preserved. No synthetic successful
try-on is supplied. Parser inference is serialized with person parsing/generation to
avoid loading a second parser instance or competing over the engine.

## Native clients / API

The studio performs all of this automatically. Existing raw-image Python/HTTP callers
remain compatible; they must opt into this preparation flow rather than assume their
old direct-generation calls magically remove the reference model.

1. Upload reference → source asset ID.
2. `POST /api/garments/prepare` with `garment`, `category`, optional `mask` asset ID.
   The reference mask must have ORIGINAL reference-photo geometry, not person geometry.
3. Poll `GET /api/garments/prepare/{id}`. The result contains `source`, prepared `garment`,
   original-geometry `mask`, `category`, and warnings/crop metadata.
4. Display the preview/mask for human review. Correct via another preparation request.
5. Submit `/api/jobs` with the prepared garment plus `preparation` (its job ID) and
   `garment_reviewed:true`, along with person, person mask, category/preset/seed.

Missing/mismatched/expired preparation or absent review is rejected when using the
prepared-reference contract. The preparation history is bounded and cleared on
restart/session reset. Re-extract if it expires. Legacy raw calls without preparation
are still supported for clients that supply already-isolated product photos.

`EdgeAIClient.prepare_garment` and `wait_garment` wrap the preparation endpoints.
`select_catalog_product` now marks its initial image `requires_preparation:true` and
returns `source_garment` as well as the legacy `garment` field.

CPU-only CLI alternative, followed by explicit visual review:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_garment.py --garment .\reference.jpg --category overall
```

Outputs: `data/prepared-garment/garment.png`, `reference-mask.png`, `preparation.json`.
It generates no person/try-on result. Use `--mask` for a manually corrected reference
mask and `--output` to keep multiple preparations separately.
