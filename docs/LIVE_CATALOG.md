# Free live clothing search — update guide

**15 October 2026 · Windows / RTX 5060 8 GB project**

This implements the accepted **free, live-first, best-effort** approach. It is not a
universal CAPTCHA/security bypass or an access guarantee. No API key, paid proxy,
ScrapingBee credits or account are needed for the default sources.

## Install over your working project

1. Stop the service with Ctrl+C. Back up any local code changes.
2. Extract **edgeai-live-catalog-update.zip** into the folder containing `main.py`,
   replacing source files. This is a cumulative catalog patch: it includes the earlier
   catalog integration. Preserve `.venv`, models, and `data`.
3. In PowerShell, from that folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_catalog.ps1
$env:EDGEAI_MEMORY="staged"
.\.venv\Scripts\python.exe main.py
```

4. Open the printed local studio URL (normally http://127.0.0.1:8000). Press Ctrl+F5
   and pair with the terminal token.

The installer adds catalog dependencies and refreshes editable package discovery;
it does not reinstall torch, CUDA, diffusers or model weights. The four default
stores do not need Playwright/Chromium. To use the older browser adapters, install
Chromium separately or run the installer with `-LegacyBrowsers`.

The alternative **edgeai-live-integrated-project.zip** contains the full source,
not installed dependencies, models, private photos or a prefetched retail catalog.
For a clean installation, follow the main Windows setup guide first, then this guide.

## Use it

1. Leave **Live search · fetch fresh products every time** checked.
2. Start with `dress`, `shirt`, `t-shirt`, or `trousers` and an INR budget.
3. Use **All free live stores** or pick one store. Optional brand/category/colour
   filters remain strict; an empty result never relaxes your budget.
4. Read the per-store status and fetched timestamps. Inspect the actual product photo.
5. **Select garment** → automatic clothing-only extraction → inspect/correct the
   reference and confirm review → capture/upload person → create/review person mask → Generate.
   See [the garment/dress update](GARMENT_AND_DRESS_FIX.md).

The selected real image becomes the same local garment asset consumed by CatVTON.
Existing camera, mask, staged-memory and dress controls remain intact. Local GPU
try-on generation uses no scraping-service credits. Selection itself reuses the
just-downloaded photo; it is not a new retailer stock check.

Uncheck Live search to deliberately browse saved observations. That mode is visibly
labelled **SAVED CATALOG · NOT LIVE**. Selecting Imported local catalog also switches
off network fetching. Saved mode is an optional convenience, not a live fallback.

## What changed

- Fresh HTTP requests on **every** live search, even for the same query with a warm DB.
- Default sources: **No Nasties, Femmella, Nobero, The Summer House**.
- Fetch publicly accessible storefront feeds, verify the storefront reports INR,
  apply filters locally, then download and validate matching real garment photos.
- Use observed available variants, decimal prices, variant colours and associated
  images. Reject ambiguous multi-colour photos, unavailable-only products, obvious
  multi-piece sets, child-labelled products and unsupported categories.
- Independently query all selected stores: one failure does not discard another
  store's results. Report HTTP errors, page limits, empty matches and image failures.
- Live results come only from that invocation's completed downloads. No DB-wide
  lookup after a failed fetch; no fake products, saved-result substitution or mock AI.
- Current per-store observation timestamps and explicit saved/live labels.
- Robots checks, approved hosts, public-IP-pinned sockets, TLS checks, redirect and
  byte limits, pacing and process-wide HTTP 429 Retry-After cooldowns. No auto-retry
  storm, CAPTCHA solver, proxy rotation or stealth browser.

## Real verification, not just fixture tests

Observed from this Linux workspace on 15 October 2026 IST. These are completed
**live network requests plus decoded product photographs**, not imported products.
For these CLI probes `limit=3` capped downloads at 3 per store and displayed the
cheapest 3 overall. The source counts below include successfully downloaded photos
from all stores, even those not among the 3 displayed cards.

| Source | Dress ≤ ₹20,000 | Shirt ≤ ₹5,000 | Trousers ≤ ₹10,000 |
|---|---:|---:|---:|
| No Nasties | 3 | 3 | 3 |
| Femmella | 3 | 3 | 3 |
| Nobero | 0 matching within scan | 3 | 3 |
| The Summer House | 3 | 3 | 3 |

Elapsed times in this one sequence: **12.40 s**, **15.27 s**, **15.22 s**. They are not
Windows measurements or performance guarantees. A normal UI search can download
more photos and take longer.

A real Chromium studio test separately returned **8 Femmella dress cards**, loaded
all authenticated thumbnails, selected a dress into an actual garment asset, and
activated the existing dress controls. Repeating the same query fetched again and
advanced the observation timestamp; explicit saved mode remained distinct. Mobile
layout and JavaScript-error checks passed. No new GPU inference was performed.

Machine-readable evidence: `docs/catalog/live-source-verification.json`.
Automated regressions: **118 passing tests** including earlier camera/AI tests and
new feed/variant/freshness/rate-limit/DNS/isolation tests. Network evidence is separate
from deterministic tests. Target Windows installation still requires your local run.

## Limits and honest failure behaviour

- These stores can later block requests, change data formats or become unavailable.
  **Free and live does not mean guaranteed.** Even a successful feed can be served
  by a retailer/CDN cache; "live" means fetched during this search, not a promise
  about the retailer's backend freshness or checkout stock.
- Up to **3 pages × 100 records per store**, stopping earlier when enough candidates
  match; **8 photos per store**, 12 image attempts. The UI displays up to 24 results
  overall. This is a bounded discovery tool, not a complete store inventory index.
- Prices are the lowest observed available variant price matching the selected
  colour, not a promise that every size costs that amount. Verify size, colour,
  final checkout price, tax/shipping and availability at the product link.
- Occasion matching is a category heuristic, not a store endorsement or a styling
  model. Try a simple garment query if a narrow query returns nothing.
- Catalog image storage is capped at 512 MB. Stop the service and back up/remove
  `data/catalog/` to reset it if full; this does not remove your model weights.
- A source can time out after about 100 seconds. Completed fresh feed photos can be
  retained with a partial/timeout status; saved old products are never substituted.
- Model-worn images can have poor framing/occlusion for try-on. Decode validation
  does not prove garment suitability, exact colour/size, or image-use permission.
- Robots permission is not a license or a guarantee of compliance with store terms.
  Check terms/image rights for your intended use; no retail photos are bundled here.
- Legacy Amazon/Myntra/Ajio remain optional and may block. They are not default
  sources and are not advertised as working. No paid scraping provider was added.

An early aiohttp probe received 429s although ordinary requests probes succeeded;
the release uses a standard requests/urllib3 transport with public-IP-pinned sockets
and the identifying research user agent. It does not escalate to another transport
or retry around a block within a search. Final live verification used the release
transport. Earlier discovery also exposed a too-large feed page and an incorrectly
classified maxi skirt; page sizing and category inference were corrected and tested.

## CLI / API

```powershell
# Live is now the default, no key required:
.\.venv\Scripts\python.exe scripts\search_catalog.py "shirt" --budget 5000
.\.venv\Scripts\python.exe scripts\search_catalog.py "dress" --source femella --budget 5000
# Explicit saved-only mode:
.\.venv\Scripts\python.exe scripts\search_catalog.py "dress" --saved
```

The API slug `femella` is retained; its current canonical store is
`https://www.femmella.com`. Other new slugs: `nonasties`, `nobero`, `summerhouse`.
Source omitted = all four free stores, not the three legacy sites.

`POST /api/catalog/search` accepts `event`, `budget`, optional filters/source/limit,
and `live` (default **true**). `live:false` means saved-only. `refresh` remains accepted
for older callers but no longer changes live behaviour: live always fetches.

The Python `scrape_if_empty` name is retained for compatibility. **True now means
always fetch live**, false means saved-only. `source='local'` is always saved-only.
Reports use `mode='live'` or `mode='local_cache'`; products include `observed_at`,
`freshness`, `available_at_fetch`, and `price_note`. The previous `live_and_cache`
mode is no longer emitted. Read source status even when products were returned.

See [CATALOG_INTEGRATION.md](CATALOG_INTEGRATION.md) for full API and storage details.
