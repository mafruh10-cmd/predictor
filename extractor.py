"""
Regex-based NLP extractor.
Parses raw article text → structured case dict.
"""

import re
import json
import logging
from typing import Optional
from config import DISTRICTS, PERPETRATOR_TYPES

logger = logging.getLogger(__name__)

# ── Victim age ───────────────────────────────────────────────────────────────
_AGE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[\s-]year[\s-]old\b", re.I),
    re.compile(r"\baged\s+(\d{1,2})\b", re.I),
    re.compile(r"\b(\d{1,2})\s+years?\s+old\b", re.I),
    re.compile(r"\ba\s+(\d{1,2})[\s-]year\b", re.I),
]

def _extract_age(text: str) -> Optional[int]:
    for pat in _AGE_PATTERNS:
        m = pat.search(text)
        if m:
            age = int(m.group(1))
            if 1 <= age <= 90:
                return age
    return None


def _age_group(age: Optional[int]) -> str:
    if age is None:
        return "unknown"
    if age < 6:   return "infant (0-5)"
    if age < 13:  return "child (6-12)"
    if age < 18:  return "minor (13-17)"
    if age < 25:  return "young adult (18-24)"
    if age < 45:  return "adult (25-44)"
    return "older adult (45+)"


# ── Victim count ─────────────────────────────────────────────────────────────
_VICTIM_COUNT_PATTERNS = [
    re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:women|girls|victims|females)\b", re.I),
]
_WORD_NUM = {"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}

def _extract_victim_count(text: str) -> int:
    for pat in _VICTIM_COUNT_PATTERNS:
        m = pat.search(text)
        if m:
            raw = m.group(1).lower()
            return _WORD_NUM.get(raw, int(raw) if raw.isdigit() else 1)
    return 1


# ── Gang rape ────────────────────────────────────────────────────────────────
_GANG_PATTERNS = re.compile(
    r"\b(gang[\s-]?rape|gang[\s-]?assault|multiple\s+(?:men|accused|perpetrators|suspects))\b", re.I
)

def _is_gang_rape(text: str) -> bool:
    return bool(_GANG_PATTERNS.search(text))


# ── Perpetrator count ────────────────────────────────────────────────────────
_PERP_COUNT_PATTERNS = [
    re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:men|boys|accused|suspects|perpetrators)\b", re.I),
]

def _extract_perp_count(text: str, gang: bool) -> int:
    for pat in _PERP_COUNT_PATTERNS:
        m = pat.search(text)
        if m:
            raw = m.group(1).lower()
            return _WORD_NUM.get(raw, int(raw) if raw.isdigit() else 1)
    return 2 if gang else 1


# ── District ─────────────────────────────────────────────────────────────────
_DISTRICT_PATTERNS = {
    d: re.compile(r"\b" + re.escape(d) + r"\b", re.I)
    for d in DISTRICTS
}

def _extract_district(text: str) -> Optional[str]:
    for district, pat in _DISTRICT_PATTERNS.items():
        if pat.search(text):
            return district
    return None


# ── Upazila (best-effort — common ones) ──────────────────────────────────────
_UPAZILA_PATTERN = re.compile(
    r"\b(\w[\w\s]+)\s+upazila\b", re.I
)

def _extract_upazila(text: str) -> Optional[str]:
    m = _UPAZILA_PATTERN.search(text)
    if m:
        return m.group(1).strip()
    return None


# ── Perpetrator type ─────────────────────────────────────────────────────────
def _extract_perp_type(text: str) -> Optional[str]:
    text_lower = text.lower()
    for ptype, keywords in PERPETRATOR_TYPES.items():
        for kw in keywords:
            if kw in text_lower:
                return ptype
    return None


# ── Case filed ───────────────────────────────────────────────────────────────
_CASE_FILED_PAT = re.compile(
    r"\b(case\s+(?:was\s+)?filed|fir\s+(?:was\s+)?lodged|filed\s+a\s+case|lodged\s+a\s+case"
    r"|complaint\s+(?:was\s+)?filed|police\s+case|filed\s+with\s+police)\b", re.I
)

def _case_filed(text: str) -> bool:
    return bool(_CASE_FILED_PAT.search(text))


# ── Arrest ────────────────────────────────────────────────────────────────────
_ARREST_PAT = re.compile(
    r"\b(arrested|detained|held|in\s+custody|remanded)\b", re.I
)

def _arrest_made(text: str) -> bool:
    return bool(_ARREST_PAT.search(text))


# ── Incident date (mentioned in article body) ────────────────────────────────
_INCIDENT_DATE_PAT = re.compile(
    r"\bon\s+(\w+\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}\s+\w+(?:\s+\d{4})?)\b", re.I
)

def _extract_incident_date(text: str) -> Optional[str]:
    m = _INCIDENT_DATE_PAT.search(text)
    if m:
        return m.group(1).strip()
    return None


# ── Keywords matched ──────────────────────────────────────────────────────────
_KEYWORD_LIST = [
    "rape", "gang rape", "sexual assault", "rape victim", "rape accused",
    "minor", "child", "girl", "woman", "arrested", "case filed",
]

def _matched_keywords(text: str) -> str:
    text_lower = text.lower()
    matched = [k for k in _KEYWORD_LIST if k in text_lower]
    return json.dumps(matched)


# ── Main entry point ─────────────────────────────────────────────────────────

def extract_case(article_row) -> Optional[dict]:
    """
    Given a sqlite3.Row from the articles table, return a case dict or None
    if the article is not a rape-case report.
    """
    content = article_row["content"] or ""
    title   = article_row["title"]   or ""
    full_text = f"{title} {content}"

    # Must mention rape explicitly
    if not re.search(r"\brap(?:e[ds]?|ing)\b|\bgang[\s-]?rape\b|\bsexual assault\b", full_text, re.I):
        return None

    age      = _extract_age(full_text)
    gang     = _is_gang_rape(full_text)
    district = _extract_district(full_text)

    return {
        "article_id":           article_row["id"],
        "source":               article_row["source"],
        "article_url":          article_row["url"],
        "article_title":        title,
        "published_date":       article_row["published_date"],
        "incident_date":        _extract_incident_date(full_text),
        "district":             district,
        "upazila":              _extract_upazila(full_text),
        "victim_age":           age,
        "victim_age_group":     _age_group(age),
        "victim_count":         _extract_victim_count(full_text),
        "perpetrator_count":    _extract_perp_count(full_text, gang),
        "perpetrator_type":     _extract_perp_type(full_text),
        "gang_rape":            int(gang),
        "case_filed":           int(_case_filed(full_text)),
        "arrest_made":          int(_arrest_made(full_text)),
        "keywords_matched":     _matched_keywords(full_text),
    }
