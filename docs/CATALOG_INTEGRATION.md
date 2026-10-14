# Catalog integration — current live-first release

For installation, live evidence, source limits and migration notes, start with
**[LIVE_CATALOG.md](LIVE_CATALOG.md)**. This guide describes the shared catalog/AI
integration. The current default is a fresh free-store search, not cache-first.

## Source integrated

- Repository: https://github.com/MichealDeSanta15/Virtual-TryOn
- Branch: `friend-2-web-scraping-pipeline`
- Reviewed commit: `1c070852cf309177fad620a5d9eca0d64c878997`

The repaired `clothing_pipeline` package is integrated into the existing working
studio. The branch's mock GUI, generated swatches, placeholder try-on and root
`main.py` did not replace the real engine. Attribution and the earlier audit are in
`docs/catalog/`. GitHub remains unchanged. The original team code has no confirmed
license grant in the reviewed branch; obtain team permission before redistribution.

## Install / workflow

Stop the service; extract **edgeai-live-catalog-update.zip** over the existing folder
with `main.py`. Preserve `.venv`, models and data. Then:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_catalog.ps1
$env:EDGEAI_MEMORY="staged"
.\.venv\Scripts\python.exe main.py
```

Reload the studio with Ctrl+F5 and pair again. The installer adds catalog dependencies,
not torch/CUDA/diffusers or new model weights. The free public-feed stores do not
need Chromium. Optional legacy browser adapters need:

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

1. Enter a garment/occasion query and INR budget. Live search is checked by default.
2. Pick all four free stores or a specific source. Review source statuses and photos.
3. Select a garment; the image becomes a source asset and sets upper/lower/overall.
   The studio now extracts clothing only, presents a correction editor and requires
   preview approval before generation. See [GARMENT_AND_DRESS_FIX.md](GARMENT_AND_DRESS_FIX.md).
   The old person mask is cleared.
4. Capture/upload the person, generate/review the mask, then run local CatVTON.

The camera, staged GPU placement, long-dress controls and safety checker are retained.
Search has a separate bounded worker; it does not load another AI model or create a
flat overlay. No GPU inference or Windows execution was newly validated here.

## Source modes

**Default live sources:** No Nasties (`nonasties`), Femmella (`femella`), Nobero
(`nobero`), The Summer House (`summerhouse`). All four passed actual fresh-feed plus
photo-download checks; see the dated evidence and limitations in the live guide.

Every live search performs network requests. Only products observed and downloaded
in that invocation can appear. A blocked source is reported; successful other stores
can still contribute. Empty results do not relax filters or reuse old products.

Uncheck Live for saved-only search, or choose Imported local catalog. The UI marks
those results as **NOT LIVE**. The database and query cache remain useful for that
explicit mode and for selecting/downloading already-observed garments.

**Optional legacy adapters:** Myntra, Ajio, Amazon India. They are individually
selectable but not included in default all-free-store searches. Earlier probes found
Myntra's robots endpoint returned HTML, Ajio returned 403, and the final Amazon probe
returned 503. Do not claim these sites work because their offline parsers pass tests.
They do not solve CAPTCHAs or circumvent access challenges. Historical evidence is
in `docs/catalog/workspace-*.json`.

## Storage / privacy

- DB: `data/catalog/products.db`; catalog photos: `data/catalog/images/`.
- Photos are normalized content-addressed PNGs; 512 MB catalog cap.
- Saved-mode query cache: ID-only SQLite, 24-hour TTL, 500-entry LRU.
- Person/selected/generated session assets: `data/assets/`.
- Delete session images removes session assets, **not** the reusable catalog.
- Reset the catalog only with the server stopped: back it up, then remove `data/catalog/`.
- Set `EDGEAI_DATA` before startup to relocate both service and catalog data. Prefer
  it over the legacy standalone `EDGEAI_CATALOG_DATA` override when using the studio.

Free-store feed filters run locally; retailers receive normal storefront/feed/image
requests, never your person photo or generated output. The legacy browser adapters
send the clothing query to their retailer search page. Local AI inference uses no
scraping credits and stays on the service machine after model setup. A hosted preview
is not your laptop: use non-sensitive images there and run locally for private photos.

## Optional real local import

This is **not** a replacement for the live workflow. It is an explicit offline mode
for photos you own or are permitted to use. No prefetched or fake catalog is bundled.
Create a JSON manifest beside your photos, replacing the illustrative fields below:

```json
[
  {
    "id": "my-blue-dress",
    "title": "Blue maxi dress",
    "brand": "Your brand",
    "price": 2500,
    "currency": "INR",
    "category": "dress",
    "occasion": "party",
    "color": "blue",
    "image_path": "photos/blue-dress.jpg",
    "image_rights_confirmed": true
  }
]
```

```powershell
.\.venv\Scripts\python.exe scripts\import_catalog.py .\my_catalog.json
```

The rights flag is your affirmation, not a license check. Unknown prices may be null
but will not satisfy numeric budgets. Invalid photos are rejected. Re-importing a
stable ID updates the record. Never import the old generated swatches as real garments.

## Python / HTTP / teammate handoff

```python
from clothing_pipeline.api import search_clothes
products = search_clothes('dress', 'under 5000', source='femella', limit=12)
# Fresh by default. To deliberately use only saved observations:
saved = search_clothes('dress', 'under 5000', scrape_if_empty=False)
```

The historical `scrape_if_empty=True` argument now means **always fetch**, regardless
of whether the DB has matching products. `refresh` is a compatibility no-op in live
mode. Call the synchronous API from a worker, not an asyncio event loop / GUI thread.
For per-source status use `ClothingPipeline.search_report`.

Products retain numeric `price`, local `image_path`, category/source fields and add
`tryon_category`, `tryon_supported`, `image_validated`, `quality_note`, `observed_at`,
`freshness`, `available_at_fetch` and `price_note`. HTTP responses omit local paths.
`freshness='fetched_this_search'` describes only that search response; saved mode uses
`saved_observation`. Legacy adapters may have unknown availability.

| Method | Authenticated endpoint | Purpose |
|---|---|---|
| POST | `/api/catalog/search` | Queue event/budget/source/filters; live defaults true |
| GET | `/api/catalog/search/{job_id}` | Poll state/result and source status |
| GET | `/api/catalog/products/{id}/image` | Normalized thumbnail |
| POST | `/api/catalog/products/{id}/select` | Product → real garment asset/category |

Selection returns `garment`, a valid asset ID for `/api/jobs`, plus category/product.
Selection reuses the saved photo; it does not claim a fresh stock check at click time.
Use `EdgeAIClient.search_catalog`, `wait_catalog`, `select_catalog_product`, or
`examples/qt_catalog_bridge.py`. Client and Qt bridge now default to live too.
The original upstream `ui/mock_services.py` is not used; replace it with real service
bridges if adopting that separate GUI.

## Bounds / verification

- One active catalog job plus one waiting job; GPU worker is separate.
- Free sources: at most 300 records / 8 photos per store; strict filters, bounded
  image attempts, roughly 100-second source deadline plus cleanup.
- Legacy sources: up to 12 cards on one browser search page.
- At least one-second process-wide per-host pacing, longer crawl-delay respected.
  HTTP 429 Retry-After cooldown persists across searches in the same process.
- Approved hosts, DNS public-address validation with pinned sockets, TLS verification,
  redirect checks, no HTTPS downgrade, response byte limits, no environment proxies.
  Legacy browser networking is not DNS-pinned like the dedicated HTTP downloader.
- Product images: up to 12 MB / 20 MP input, at least 96px on the short side; normalized
  to at most 2048px. Validation is not proof of framing, rights or try-on fidelity.
- Saved-mode DB candidate search is bounded to 2,000 recent matches before ranking.
- 118 automated tests pass; real network and studio checks are described in the live
  guide. No claims of Windows/GPU throughput or guaranteed retailer availability.

This is a research service, not an internet-exposed production catalog gateway.
Review store terms and image permissions separately from technical access.
