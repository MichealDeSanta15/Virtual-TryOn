"""Fixed public storefronts; no user-supplied hosts or paid API keys."""
FEED_STORES = {
    'nonasties': ('No Nasties', 'https://www.nonasties.in'),
    'femella': ('Femmella', 'https://www.femmella.com'),
    'nobero': ('Nobero', 'https://nobero.com'),
    'summerhouse': ('The Summer House', 'https://thesummerhouse.in'),
}
DEFAULT_SOURCES = tuple(FEED_STORES)
LEGACY_SOURCES = ('myntra', 'ajio', 'amazon')
LIVE_SOURCES = DEFAULT_SOURCES + LEGACY_SOURCES
ALL_SOURCES = LIVE_SOURCES + ('local',)
