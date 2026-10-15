> Historical audit of the original three-retailer integration. The current release
> adds four free public-feed sources and changes live search to fresh-only. See
> [../LIVE_CATALOG.md](../LIVE_CATALOG.md) for current behaviour and live evidence.

# Friend 2 branch audit and changes

Reviewed public branch commit `1c070852cf309177fad620a5d9eca0d64c878997`.
The baseline import was executed and failed with:
`ModuleNotFoundError: No module named 'clothing_pipeline.cache'`.

| Finding in reviewed branch | Integration change |
|---|---|
| API/search import absent cache package; broad `cache/` ignore rule can hide source | Added cache implementation + explicit source unignore rules |
| `scraper.py` passes `scrape_if_empty=False`; catches exceptions as empty results | Real API exported; studio has explicit live/cache/refresh controls and source diagnostics |
| Global API injects one SQLite connection across callers | Service uses per-operation connections with WAL/busy timeout and serialized network searches |
| Upsert returns `cursor.lastrowid` after UPDATE | Looks up stable ID by unique source URL |
| Decimal price parser removes dots; budget parser damages commas/words | Separate price/budget parsing, decimals/Indian comma formats retained; invalid budgets rejected |
| Fallback search relaxes filters, returns fabricated metadata and colored text images | No filter-dropping fallback; no generated production products; explicit real-photo importer |
| Query cache missing TTL/LRU code | 24-hour fixed TTL, ID-only persistent cache, 500-entry LRU; current fields rechecked on hit |
| Search requires title to include broad phrase like `wedding outfit` | Occasion/category-aware matching, with explicit price/source/category/brand/color retained |
| `shirt` substring checked before `t-shirt`; query can override product category | Title-first bounded category rules, compound shirt-dress handling, explicit AI mapping |
| Multi-piece/unknown categories can flow into generic overlay | Unmapped sets/sarees/etc. cannot silently be treated as supported single garments |
| Robots blocking I/O, no timeout and permissive failure behavior | Bounded async robots retrieval, wildcard-aware parser, fail closed on uncertainty |
| Stealth injection, browser resources leak if startup fails | No stealth injection/CAPTCHA bypass; bounded cleanup in finally, source isolation |
| Parallel unbounded image reads into `.jpg` filenames, no decode check | Approved CDN/public-address policy, checked redirects, byte/pixel bounds, pooled connection, decode/normalize and hash dedup |
| Relative card links / data-src placeholders mishandled | URL resolution and lazy-image fallback; Ajio anchor-self links supported |
| Amazon selector union can choose brand heading as title | Candidate title extraction no longer relies on selector-list order; brand-only cards rejected |
| Missing cached image still returned for try-on | Product image revalidated before returning/selection; invalid records excluded |
| Blank source URLs can collide in SQLite UNIQUE column | Reject records without a unique source URL |
| GUI mock/placeholder engine can disguise integration failures | Keep working real CatVTON service; errors stay explicit; no branch mock GUI copied |

## What remains external / unproven

- Retailer availability, policy, changing markup, completeness, live price/stock.
- Computer vision cannot infer copyright permission from a product thumbnail.
- Photo decoding is not semantic garment isolation or a promise of suitable framing.
- Multi-piece, ethnic wear, garment size, exact logos/fit remain model limitations.
- Native Windows browser lifecycle and final catalog→GPU run need target-machine testing.

## Source / license handling

The original branch's README says `MIT (or choose your own)` but there is no explicit
repository LICENSE file at the inspected commit. We do not treat that wording as a
confirmed MIT grant. This is a user-requested team integration; retain the original
team's authorship and obtain clear permission/license terms before public redistribution
or commercial use. CatVTON's existing non-commercial license restrictions still apply.
The project-root CC license does not relicense third-party/team code automatically.
