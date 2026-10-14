"""Search for casual men's jeans."""
from clothing_pipeline.api import search_clothes

print("=" * 70)
print("  Searching: Casual Men's Jeans")
print("=" * 70)

results = search_clothes(
    event="casual",
    budget="5000",
    category="jeans",
    scrape_if_empty=False,
)

if results:
    print(f"\nFound {len(results)} result(s):\n")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r.get('brand', '?')} - {r.get('title', '?')}")
        print(f"      Price:    Rs. {r.get('price', 0):,.0f}")
        print(f"      Category: {r.get('category', '?')}")
        print(f"      Color:    {r.get('color', '?')}")
        print(f"      Occasion: {r.get('occasion', '?')}")
        print(f"      Sizes:    {r.get('sizes', 'N/A')}")
        print(f"      Image:    {r.get('image_path', 'none')}")
        print(f"      Source:   {r.get('source', '?')}")
        print()
else:
    print("\nNo results found in fallback dataset.")
    print("Trying broader search without category filter...\n")
    
    results = search_clothes(
        event="casual",
        budget="5000",
        scrape_if_empty=False,
    )
    
    print(f"Found {len(results)} result(s):\n")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r.get('brand', '?')} - {r.get('title', '?')}")
        print(f"      Price: Rs. {r.get('price', 0):,.0f} | {r.get('category', '?')} | {r.get('color', '?')}")
        print()

print("Done!")
