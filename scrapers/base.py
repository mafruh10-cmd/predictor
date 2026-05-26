"""Base scraper with retry logic, rate limiting, and progress tracking."""

import time
import logging
import requests
from typing import List, Optional
from config import REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class BaseScraper:
    SOURCE = "unknown"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def fetch(self, url: str, params: dict = None) -> Optional[str]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True,
                )
                resp.raise_for_status()
                time.sleep(REQUEST_DELAY_SECONDS)
                return resp.text
            except requests.RequestException as e:
                wait = 2 ** attempt
                logger.warning(f"[{self.SOURCE}] attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
        logger.error(f"[{self.SOURCE}] giving up on {url}")
        return None

    def get_article_urls(self, keyword: str, year: int) -> List[dict]:
        """Return list of dicts: {url, title, date}. Override in subclass."""
        raise NotImplementedError

    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch and return plain-text body of an article. Override in subclass."""
        raise NotImplementedError
