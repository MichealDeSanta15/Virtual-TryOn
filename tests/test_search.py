"""
Tests for the search engine.
"""

from clothing_pipeline.search.engine import SearchEngine


def test_parse_budget_single_value():
    assert SearchEngine.parse_budget("5000") == (None, 5000.0)
    assert SearchEngine.parse_budget("₹5000") == (None, 5000.0)


def test_parse_budget_range():
    assert SearchEngine.parse_budget("2000-5000") == (2000.0, 5000.0)
    assert SearchEngine.parse_budget("1000 to 3000") == (1000.0, 3000.0)


def test_parse_budget_directional():
    assert SearchEngine.parse_budget("under 2000") == (None, 2000.0)
    assert SearchEngine.parse_budget("above 3000") == (3000.0, None)
    assert SearchEngine.parse_budget("upto 4000") == (None, 4000.0)


def test_parse_budget_empty():
    assert SearchEngine.parse_budget("") == (None, None)
    assert SearchEngine.parse_budget("abc") == (None, None)


def test_occasion_mapping():
    info = SearchEngine.get_occasion_info("wedding")
    assert info["occasion_tag"] == "wedding"
    assert len(info["keywords"]) > 0

    info = SearchEngine.get_occasion_info("party")
    assert info["occasion_tag"] == "party"

    # Unknown event should still return something usable
    info = SearchEngine.get_occasion_info("graduation")
    assert info["occasion_tag"] == "graduation"
    assert len(info["keywords"]) > 0


def test_occasion_partial_match():
    info = SearchEngine.get_occasion_info("beach party")
    assert info["occasion_tag"] in ("beach", "party")


if __name__ == "__main__":
    test_parse_budget_single_value()
    print("✓ test_parse_budget_single_value passed")

    test_parse_budget_range()
    print("✓ test_parse_budget_range passed")

    test_parse_budget_directional()
    print("✓ test_parse_budget_directional passed")

    test_parse_budget_empty()
    print("✓ test_parse_budget_empty passed")

    test_occasion_mapping()
    print("✓ test_occasion_mapping passed")

    test_occasion_partial_match()
    print("✓ test_occasion_partial_match passed")

    print("\n✅ All search tests passed!")
