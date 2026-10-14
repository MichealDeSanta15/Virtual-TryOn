"""
robots.txt checker — respects crawling rules per domain.
"""

import logging
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RobotsChecker:
    """
    Caches and checks robots.txt for multiple domains.

    Usage:
        checker = RobotsChecker()
        if checker.can_fetch("https://www.myntra.com/some-page"):
            # proceed to scrape
    """

    def __init__(self, user_agent: str = "*"):
        self.user_agent = user_agent
        self._parsers: Dict[str, RobotFileParser] = {}

    def _get_parser(self, url: str) -> Optional[RobotFileParser]:
        """Get or create a RobotFileParser for the domain of the given URL."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self._parsers:
            robots_url = f"{domain}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
                logger.info("Loaded robots.txt for %s", domain)
            except Exception as e:
                logger.warning(
                    "Failed to load robots.txt for %s: %s", domain, e
                )
                # If we can't load robots.txt, be permissive
                return None
            self._parsers[domain] = rp

        return self._parsers[domain]

    def can_fetch(self, url: str) -> bool:
        """
        Check if the given URL is allowed by robots.txt.

        Returns True if:
        - robots.txt could not be loaded (fail-open)
        - The URL is allowed for our user agent
        """
        parser = self._get_parser(url)
        if parser is None:
            return True

        allowed = parser.can_fetch(self.user_agent, url)
        if not allowed:
            logger.warning("Blocked by robots.txt: %s", url)
        return allowed

    def crawl_delay(self, url: str) -> Optional[float]:
        """Get the crawl-delay directive for the domain, if any."""
        parser = self._get_parser(url)
        if parser is None:
            return None
        try:
            delay = parser.crawl_delay(self.user_agent)
            return float(delay) if delay else None
        except Exception:
            return None
