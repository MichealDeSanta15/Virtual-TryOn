"""Quick smoke test of the public API using fallback data."""

from clothing_pipeline.api import search_clothes, get_stats

print("=== Wedding outfit search (budget: 5000) ===")
results = search_clothes(event="wedding", budget="5000", scrape_if_empty=False)
print(f"Found {len(results)} results:\n")
for r in results:
    brand = r.get("brand", "?")
    title = r.get("title", "?")
    price = r.get("price", 0)
    cat = r.get("category", "?")
    img = "yes" if r.get("image_path") else "no"
    print(f"  {brand:20s} | {title:35s} | Rs.{price:>8,.0f} | {cat:12s} | img: {img}")

print("\n=== Party outfit search (budget: 2000-8000) ===")
results2 = search_clothes(event="party", budget="2000-8000", scrape_if_empty=False)
print(f"Found {len(results2)} results:\n")
for r in results2:
    brand = r.get("brand", "?")
    title = r.get("title", "?")
    price = r.get("price", 0)
    print(f"  {brand:20s} | {title:35s} | Rs.{price:>8,.0f}")

print("\n=== Pipeline Stats ===")
stats = get_stats()
for k, v in stats.items():
    print(f"  {k}: {v}")

print("\nDone!")
