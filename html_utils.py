"""Minimal HTML parsing helpers using stdlib only (no BeautifulSoup)."""

import re
from html.parser import HTMLParser
from typing import List, Tuple, Optional


class _LinkParser(HTMLParser):
    """Collect all <a href=...> links with their text."""

    def __init__(self):
        super().__init__()
        self.links: List[Tuple[str, str]] = []   # (href, text)
        self._current_href: Optional[str] = None
        self._buf: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_d = dict(attrs)
            self._current_href = attrs_d.get("href", "")
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "a" and self._current_href is not None:
            self.links.append((self._current_href, " ".join(self._buf).strip()))
            self._current_href = None
            self._buf = []

    def handle_data(self, data):
        if self._current_href is not None:
            self._buf.append(data)


class _MetaParser(HTMLParser):
    """Extract <meta> and <title> tags."""

    def __init__(self):
        super().__init__()
        self.meta: dict = {}
        self.title: str = ""
        self._in_title = False
        self._title_buf: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attrs_d = dict(attrs)
            name    = attrs_d.get("name") or attrs_d.get("property") or ""
            content = attrs_d.get("content", "")
            if name and content:
                self.meta[name.lower()] = content
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.title = " ".join(self._title_buf).strip()
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)


class _TextExtractor(HTMLParser):
    """Extract visible text, skipping script/style blocks."""

    SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "header"}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self._parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            text = data.strip()
            if text:
                self._parts.append(text)

    def get_text(self) -> str:
        return " ".join(self._parts)


def extract_links(html: str) -> List[Tuple[str, str]]:
    p = _LinkParser()
    p.feed(html)
    return p.links


def extract_meta(html: str) -> Tuple[dict, str]:
    """Return (meta_dict, title)."""
    p = _MetaParser()
    p.feed(html)
    return p.meta, p.title


def extract_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    return p.get_text()


def resolve_url(base: str, href: str) -> str:
    """Resolve a possibly-relative href against a base URL."""
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        scheme = base.split("://")[0]
        return f"{scheme}:{href}"
    if href.startswith("/"):
        # absolute path on same host
        parts = base.split("/")
        return "/".join(parts[:3]) + href
    # relative path — naive join
    base_dir = "/".join(base.rstrip("/").split("/")[:-1])
    return f"{base_dir}/{href}"


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()
