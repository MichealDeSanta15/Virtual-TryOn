# Verification report

**Build session:** 15 October 2026 (user timezone Asia/Calcutta).
**Target:** Windows + RTX 5060 8 GB.
**Actual test environment:** Linux sandbox, Python 3.13.16, no NVIDIA GPU, no torch,
no downloaded model weights. Target installation instructions use Python 3.11.

## Executed checks

### Automated Python suite

Command: `python -m pytest -q`

**Result: 22 passed.** One dependency deprecation warning from the sandbox's
FastAPI/Starlette TestClient using httpx. It did not affect the test outcome.

Coverage:

- BGR/RGB conversion, input-shape contract, reversible letterbox geometry.
- No accidental center crop; mask validation and binary mask interpolation.
- Bit-exact outside-mask preservation, face/hand label protection in mask construction.
- Latest-frame copy isolation, stale frame behavior and frame sequence handling.
- Asset validation, invalid-file rejection, traversal rejection and cleanup.
- One-active/one-pending worker behavior, queue overflow, cancellation and recovery.
- API authorization, upload/mask/job/result contract, invalid request/category handling.
- Camera snapshot color/size contract and no-camera errors.
- **Actual aiortc WebRTC loopback:** synthetic sender negotiates with receiver over
  local UDP, sends video, and decoded BGR frames arrive with expected geometry/color.

API tests intentionally use a `TestOnlyEngine` double **only inside tests**. These
verify orchestration, not real image synthesis. Production has no mock backend.
Mask-class tests use synthetic label maps; they are not learned-parser accuracy tests.

### Browser checks

Headless Chromium / Playwright:

- Desktop 1440px layout loads without JavaScript errors.
- Pairing token accepted and status updates.
- Person/garment uploads work.
- Canvas mask painting works.
- Generate request is submitted; absent AI dependencies return a visible **FAILED**
  state and explicit setup error, not a placeholder result.
- Camera/photo tab switching and phone-publisher page load.
- Mobile 390px layout has no horizontal page overflow.

Synthetic colored test rectangles were used for upload tests. They were not diffusion
outputs and are not bundled as convincing-looking result images.
The included [studio screenshot](screenshots/studio.png) shows the actual empty UI.

### Static / service checks

- Python `compileall` on application, scripts, vendor wrapper and examples.
- JavaScript syntax check using `node --check edgeai/web/app.js`.
- `main.py` starts, serves `/health` and authenticated endpoints; local live preview
  binds to 0.0.0.0 with no preview host restriction.
- Upstream CatVTON source pinned to a real commit; model snapshot revisions and file
  names verified against Hugging Face model metadata.
- GPU/model diagnostics saved in `workspace-diagnostics.json` showing **not ready**.

## Not executed / not verified

- Windows setup script execution or the pinned GPU Python environment on Windows.
- RTX 5060 inference, BF16 CUDA kernels, CPU-offload behavior, OOM thresholds.
- Learned SegFormer parser inference or optional MediaPipe pose execution.
- Full model weight download, model initialization, upstream safety checker execution.
- Actual try-on quality on any real photograph or any clothing category.
- Physical Android/iOS WebRTC pairing, HTTPS CA trust, LAN firewall or camera drivers.
- Physical IP Webcam/DroidCam feed capture, reconnect under actual Wi-Fi loss.
- PyQt6 integration in Member 1's real application or Member 2's real catalog.
- Inference FPS, latency, end-to-end phone latency, energy use or VRAM on the target GPU.

**Consequently:** this package is implemented and CPU/integration-tested, not an
end-to-end GPU-validated finished product. No benchmark values are invented.

## Acceptance run on your laptop

1. Follow `SETUP_WINDOWS.md` and run doctor. Save `data/my-diagnostics.json`.
2. Run `scripts/tryon.py` with a consenting adult portrait and clean shirt product photo.
3. If auto mask is wrong, review/edit the mask in the studio and repeat.
4. Run three repetitions on identical inputs/seed to separate cold/warm timing.
5. Repeat for a lower-body garment and a dress with full-body photos.
6. Review original/reference/mask/raw/final images. Confirm folds/body alignment,
   seams, identity and garment details rather than only "it generated an image".
7. Test camera separately first, then capture→try-on. Keep the live feed responsive.
8. Integrate Member 1's worker signals and Member 2's local-image contract.

Use `docs/ACCEPTANCE_CHECKLIST.md` to record results. Share the diagnostic JSON and
complete traceback if model setup/inference fails; do not claim target performance
until this run has actually completed.


## Follow-up: VAE offload regression fix

After the initial build, CPU PyTorch and the pinned AI libraries were installed to
reproduce the reported meta-tensor failure using real Accelerate hooks and tiny
Diffusers models. The full suite now has **32 passing tests**. Repeated VAE
encode/decode and a tiny CatVTON denoising path are exercised with offload enabled.
These are random-weight CPU execution tests, not trained try-on quality or target
CUDA/VRAM tests. See `FIX_META_OFFLOAD.md` for exact changes and test details.
The original environment description and workspace diagnostic above describe the
initial build, before those CPU AI dependencies were installed.


## Follow-up: speed and dress controls

The cumulative update has **44 passing automated tests**. It adds repeated tiny-model
CPU execution in staged/resident modes in addition to sequential offload, placement
order checks, checkpoint-format selection and dress-mask geometry/protection tests.
Chromium checks for the new controls/status/mobile layout pass. An actual saved
tiny Diffusers .bin was loaded through the explicit format selector. These tests
are not target-GPU benchmarks or validation of learned dress fidelity. See
`SPEED_AND_DRESSES.md` for installation and the remaining acceptance work.


## Follow-up: Friend 2 catalog integration

**88 tests pass**, including the existing 44 tests and new budget, decimal price,
filter preservation, stable upsert IDs, cache TTL/LRU, threading, image validation,
robots/URL policy, import and API handoff checks. All three adapters parse offline
HTML fixtures in Chromium. A browser test used an isolated, explicitly synthetic
local catalog to exercise search -> thumbnail -> select -> actual garment asset ->
dress controls; no fixture is installed as a production fallback.

Live source observations and important limitations are recorded in
`docs/CATALOG_INTEGRATION.md` and `docs/catalog/workspace-*.json`. In particular,
initial Amazon image retrieval does not establish final metadata accuracy: a title
selector issue was found and fixed, but the final live validation received HTTP 503.
Myntra/Ajio policy/access checks stopped scraping. No new GPU synthesis or Windows
browser test was performed here. GitHub was read only; no remote writes.


## Follow-up: free live-first clothing sources

**118 tests pass** (one pre-existing Starlette/httpx warning). New regressions cover
strict feed prices/currency, availability and variant-colour/image mapping, category
priority for maxi/midi skirts, bounded discovery, partial failures, fresh-only result
isolation, repeated-query fetching, explicit saved mode, default source selection,
source-failure isolation, 429 cooldown, redirect rejection and DNS-pinned public sockets.

Real network probes returned decoded garment photos from No Nasties, Femmella, Nobero
and The Summer House. Shirts/trousers succeeded on all four; dresses had no matching
Nobero products within the bounded scan. CLI probes took 12.40–15.27 seconds in one
sequence with limit=3, not a Windows benchmark or availability guarantee.

The actual studio browser test used real live Femmella dresses (8 cards), waited for
all real authenticated thumbnails to load, selected a valid garment asset, verified
the existing dress controls, repeated the same live search with a newer observation
timestamp, and checked explicit saved-only labelling, mobile width and no JS errors.
No fixture was used as production catalog data. No final AI image was generated here.

See `LIVE_CATALOG.md` and `catalog/live-source-verification.json` for exact results,
initial failures/corrections and remaining limits. Final compileall and JS syntax
checks passed. Windows/GPU stack is preserved but not rerun in this environment.


## Follow-up: garment-only reference and dress mask preparation

**131 tests pass** (one existing dependency warning). Adds category-aware reference
segmentation, inner clothing-panel retention without filling skin/background holes,
manual selection/crop/colour contracts, alpha handling, opt-in proximal sleeve masks,
API review/category binding and missing-parser failure tests. No original model-photo
fallback is used by the studio on extraction failure.

The actual pinned clothes parser ran on CPU on the user's screenshot-cropped brown
dress. Its final extracted reference removes the visible wearer/background; about
44.04% of source pixels are retained (not an accuracy score). Browser upload and real
saved-catalog selection both exercised learned extraction, review gating and category
invalidation. Manual correction, actual CPU person masking and mobile layout checks
passed. Compileall and both JS syntax checks passed.

No new GPU diffusion/Windows execution or dress-fidelity test was performed. See
`GARMENT_AND_DRESS_FIX.md` and `garment-preparation-verification.json`. The source
reference/editor images used in testing are not included in the source archives.
<<<<<<< HEAD


## Follow-up: portrait camera orientation

Added 16 passing camera-orientation tests and an actual browser/API check with a
synthetic sideways test frame (768×512). Preview and saved capture/editor both became
512×768 portrait without CSS rotation, stretching or cropping. Source-mode reset,
remembered preference, mobile width and no JS errors were verified. The synthetic
camera fixture is not a production source and is excluded from source archives.

Current refreshed Linux sandbox result: **137 passed, 2 skipped, 1 warning (5.28s)**.
Torch is not installed in this sandbox instance: the existing offload-runtime module
and one staged-placement test were skipped. Earlier GPU/memory checks are historical,
not rerun here. No physical phone/Windows camera or GPU inference test was performed.
Compilation and both JavaScript syntax checks passed. See `CAMERA_ORIENTATION.md`
and `camera-orientation-verification.json` for details and physical-rotation limits.
=======
>>>>>>> origin/main
