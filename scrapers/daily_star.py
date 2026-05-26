"""Scraper for The Daily Star (thedailystar.net)."""

import re
import logging
from typing import List, Optional
from html_utils import extract_links, extract_meta, extract_text, resolve_url, clean_text
from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL   = "https://www.thedailystar.net"
SEARCH_URL = "https://www.thedailystar.net/search"


class DailyStarScraper(BaseScraper):
    SOURCE = "daily_star"

    def get_article_urls(self, keyword: str, year: int) -> List[dict]:
        results = []
        for page in range(0, 50):           # up to 50 pages per keyword/year
            html = self.fetch(SEARCH_URL, params={
                "query": f"{keyword} {year}",
                "page":  page,
            })
            if not html:
                break

            links = extract_links(html)
            found = 0
            for href, text in links:
                # Daily Star article URLs look like /news/... or /crime/...
                if not href:
                    continue
                full = resolve_url(BASE_URL, href)
                if (
                    full.startswith(BASE_URL)
                    and re.search(r"/\d{4}/\d{2}/\d{2}/", full)   # date in URL
                    and text.strip()
                ):
                    results.append({"url": full, "title": text.strip(), "date": ""})
                    found += 1

            logger.info(f"[daily_star] keyword='{keyword}' year={year} page={page}: {found} links")

            # stop if search returned no results (empty page)
            if found == 0:
                break

        return results

    def fetch_article_content(self, url: str) -> Optional[str]:
        html = self.fetch(url)
        if not html:
            return None

        meta, title = extract_meta(html)

        # Grab published date from meta
        date = (
            meta.get("article:published_time")
            or meta.get("pubdate")
            or meta.get("date")
            or _date_from_url(url)
            or ""
        )

        text = extract_text(html)
        text = clean_text(text)

        # Daily Star wraps article body in <div class="field-items"> or similar;
        # heuristic: keep sentences that contain rape-related keywords
        return _filter_relevant(text), date


def _date_from_url(url: str) -> str:
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def _filter_relevant(text: str) -> str:
    """Keep only paragraphs/sentences that look like article body content."""
    # Remove very short fragments (nav items, ads)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = [s for s in sentences if len(s) > 40]
    return " ".join(kept)
