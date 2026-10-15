"""Async robots policy: wildcard-aware, bounded requests, fail closed on uncertainty."""
import re
from urllib.parse import urlsplit
from protego import Protego
from clothing_pipeline.config import USER_AGENT


class RobotsChecker:
    def __init__(self, transport, user_agent=USER_AGENT):
        self.transport, self.user_agent = transport, user_agent
        self.parsers = {}
        self.reasons = {}
        self.locks = {}

    @staticmethod
    def _looks_like_robots(data):
        text = data.decode('utf-8','replace').lstrip('\ufeff')
        active = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
        if not active:
            return True  # An explicitly empty/comment-only policy has no restrictions.
        return (not text.lstrip().startswith(('<','{','[')) and
                any(re.match(r'(?i)^(user-agent|allow|disallow|sitemap|host|crawl-delay|request-rate)\s*:', line) for line in active))

    async def can_fetch(self, url):
        import asyncio
        parsed = urlsplit(url)
        origin = f'{parsed.scheme}://{parsed.netloc}'
        lock = self.locks.setdefault(origin, asyncio.Lock())
        async with lock:
            if origin not in self.parsers:
                try:
                    status, data, _ = await self.transport.get(origin+'/robots.txt', max_bytes=512*1024, respect_robots=False)
                    if status in (404,410):
                        self.parsers[origin] = Protego.parse('User-agent: *\nAllow: /')
                        self.reasons[origin] = 'No robots file (404/410); check site terms separately'
                    elif status == 200 and self._looks_like_robots(data):
                        self.parsers[origin] = Protego.parse(data.decode('utf-8','replace'))
                        self.reasons[origin] = 'Loaded robots policy'
                    else:
                        self.parsers[origin] = None
                        self.reasons[origin] = f'Robots unavailable/blocked (HTTP {status}); not scraping'
                except Exception as exc:
                    self.parsers[origin] = None
                    self.reasons[origin] = f'Robots fetch failed; not scraping: {type(exc).__name__}'
            parser = self.parsers[origin]
            if parser is None: return False
            delay = parser.crawl_delay(self.user_agent)
            if delay is not None:
                self.transport.limiter(url).min_delay = max(1.0, float(delay))
            return parser.can_fetch(url, self.user_agent)

    def reason(self, url):
        parsed = urlsplit(url)
        return self.reasons.get(f'{parsed.scheme}://{parsed.netloc}', 'Robots policy not loaded')
