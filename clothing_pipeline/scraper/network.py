"""Bounded, public-host-only HTTP for retailer metadata, robots and product images."""
import asyncio
import hashlib
import ipaddress
import time
import threading
from urllib.parse import urlsplit, urljoin
import aiohttp
from aiohttp.resolver import DefaultResolver
from clothing_pipeline.config import USER_AGENT, MAX_IMAGE_BYTES, MAX_CATALOG_BYTES
from clothing_pipeline.validation import normalized_image

DOMAINS = ('myntra.com','myntassets.com','myntraassets.com','ajio.com','ajioimg.com',
           'nonasties.in','femella.in','femmella.com','nobero.com','thesummerhouse.in','cdn.shopify.com',
           'amazon.in','amazon.com','media-amazon.com','ssl-images-amazon.com','images-amazon.com')


def allowed_url(url):
    try:
        p = urlsplit(url)
        host = (p.hostname or '').lower()
        return (p.scheme in ('http','https') and not p.username and not p.password
                and p.port in (None,80,443)
                and any(host == d or host.endswith('.'+d) for d in DOMAINS))
    except ValueError:
        return False


class PublicResolver(DefaultResolver):
    async def resolve(self, host, port=0, family=0):
        records = await super().resolve(host, port, family)
        if not records or any(not ipaddress.ip_address(r['host']).is_global for r in records):
            raise OSError('Non-public destination refused')
        return records


_RATE_LOCK = threading.Lock()
_RATE_NEXT = {}
_RATE_BLOCKED = {}


class RateLimiter:
    def __init__(self, min_delay=1.0, key=None):
        self.min_delay = min_delay
        self.key = key if key is not None else object()

    async def wait(self):
        # A process-wide reservation survives the new event loop used for each
        # search. No asyncio lock is shared between Windows worker loops.
        with _RATE_LOCK:
            now = time.monotonic()
            reserved = max(now, _RATE_NEXT.get(self.key, 0.0) + self.min_delay)
            _RATE_NEXT[self.key] = reserved
        await asyncio.sleep(max(0.0, reserved-time.monotonic()))


class SafeTransport:
    def __init__(self, image_dir):
        self.image_dir = image_dir
        self.limits = {}
        self.session = None
        self.robots = None

    async def __aenter__(self):
        from .robots import RobotsChecker
        self.robots = RobotsChecker(self)
        return self

    async def __aexit__(self, *args):
        pass  # Each bounded HTTP call owns and closes its session.

    def limiter(self, url):
        host = urlsplit(url).hostname
        return self.limits.setdefault(host, RateLimiter(key=host))

    async def get(self, url, max_bytes=MAX_IMAGE_BYTES, respect_robots=True):
        current = url
        for _ in range(4):
            if not allowed_url(current): raise ValueError('Unapproved remote host or URL')
            host = urlsplit(current).hostname
            with _RATE_LOCK:
                cooldown = _RATE_BLOCKED.get(host, 0) - time.monotonic()
            if cooldown > 0:
                raise ValueError(f'Retailer rate-limit cooldown: try again after {int(cooldown)+1} seconds')
            if respect_robots and not await self.robots.can_fetch(current):
                raise ValueError('URL blocked or robots policy unavailable')
            await self.limiter(current).wait()
            from .public_http import fetch_public
            status, data, headers = await asyncio.to_thread(fetch_public, current, max_bytes)
            # Case-insensitive access regardless of the HTTP library's serialization.
            headers = {k.lower():v for k,v in headers.items()}
            if status in (301,302,303,307,308):
                target = urljoin(current, headers.get('location',''))
                if current.startswith('https:') and not target.startswith('https:'):
                    raise ValueError('HTTPS downgrade refused')
                current = target
                continue
            if status == 429:
                # Honor Retry-After without keeping the UI worker asleep for minutes.
                from email.utils import parsedate_to_datetime
                from datetime import datetime, timezone
                retry = headers.get('retry-after', '60')
                try: delay = max(1, float(retry))
                except ValueError:
                    try: delay = max(1, (parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds())
                    except (ValueError, TypeError, OverflowError): delay = 60
                import math
                if not math.isfinite(delay): delay = 60
                with _RATE_LOCK:
                    _RATE_BLOCKED[host] = time.monotonic()+delay
            return status, data, current
        raise ValueError('Too many redirects')

    async def download_image(self, url):
        status, data, _ = await self.get(url)
        if status != 200: raise ValueError(f'Image HTTP {status}')
        image = await asyncio.to_thread(normalized_image, data)
        self.image_dir.mkdir(parents=True,exist_ok=True)
        from io import BytesIO
        buf = BytesIO();image.save(buf,format='PNG');normalized = buf.getvalue()
        key = hashlib.sha256(normalized).hexdigest()
        path = self.image_dir / (key+'.png')
        if not path.exists():
            total = sum(p.stat().st_size for p in self.image_dir.glob('*.png'))
            if total + len(normalized) > MAX_CATALOG_BYTES: raise ValueError('Catalog image cache full (512 MB)')
            temp = path.with_suffix('.tmp');temp.write_bytes(normalized);temp.replace(path)
        return str(path.resolve())
