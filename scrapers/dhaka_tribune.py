"""Scraper for Dhaka Tribune (dhakatribune.com)."""

import re
import logging
from typing import List, Optional
from html_utils import extract_links, extract_meta, extract_text, resolve_url, clean_text
from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL   = "https://www.dhakatribune.com"
SEARCH_URL = "https://www.dhakatribune.com/search"


class DhakaTribuneScraper(BaseScraper):
    SOURCE = "dhaka_tribune"

    def get_article_urls(self, keyword: str, year: int) -> List[dict]:
        results = []
        for page in range(1, 51):
            html = self.fetch(SEARCH_URL, params={
                "q":    f"{keyword} {year}",
                "page": page,
            })
            if not html:
                break

            links = extract_links(html)
            found = 0
            for href, text in links:
                if not href:
                    continue
                full = resolve_url(BASE_URL, href)
                if (
                    full.startswith(BASE_URL)
                    and re.search(r"/\d{4}/\d{2}/\d{2}/", full)
                    and text.strip()
                ):
                    results.append({"url": full, "title": text.strip(), "date": ""})
                    found += 1

            logger.info(f"[dhaka_tribune] keyword='{keyword}' year={year} page={page}: {found} links")
            if found == 0:
                break

        return results

    def fetch_article_content(self, url: str) -> Optional[str]:
        html = self.fetch(url)
        if not html:
            return None

        meta, title = extract_meta(html)
        date = (
            meta.get("article:published_time")
            or meta.get("pubdate")
            or _date_from_url(url)
            or ""
        )
        # Normalise ISO datetime to date only
        if "T" in date:
            date = date.split("T")[0]

        text = clean_text(extract_text(html))
        return text, date


def _date_from_url(url: str) -> str:
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""
