"""
Scraper module interface.
To be implemented by Friend 2 with Playwright / SQLite caching.
"""
from typing import List, Dict, Any


def search_clothes(event_text: str, budget_text: str) -> List[Dict[str, Any]]:
    """
    Search clothing items matching the event and budget.
    Placeholder until Friend 2 connects the live scraper/database.
    """
    # Returning empty list will allow mock_services to fall back to sample clothing
    return []
