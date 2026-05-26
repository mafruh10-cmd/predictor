"""
Regex-based NLP extractor.
Parses raw article text → structured case dict covering:
  - Location & incident details
  - Victim demographic + psychological profile
  - Perpetrator demographic + psychological profile
  - Justice / outcome
"""

import re
import json
import logging
from typing import Optional, Tuple
from config import DISTRICTS, PERPETRATOR_TYPES

logger = logging.getLogger(__name__)

_WORD_NUM = {
    "one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
    "seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,
}

# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _word_to_int(s: str) -> int:
    s = s.lower().strip()
    return _WORD_NUM.get(s, int(s) if s.isdigit() else 1)


def _first_match(patterns: list, text: str) -> Optional[re.Match]:
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m
    return None


# ════════════════════════════════════════════════════════════════════════════
# LOCATION
# ════════════════════════════════════════════════════════════════════════════

_DISTRICT_PATTERNS = {
    d: re.compile(r"\b" + re.escape(d) + r"\b", re.I) for d in DISTRICTS
}

def _extract_district(text: str) -> Optional[str]:
    for district, pat in _DISTRICT_PATTERNS.items():
        if pat.search(text):
            return district
    return None


_UPAZILA_PAT = re.compile(r"\b([\w]+(?:\s+[\w]+)?)\s+upazila\b", re.I)

def _extract_upazila(text: str) -> Optional[str]:
    m = _UPAZILA_PAT.search(text)
    return m.group(1).strip() if m else None


_URBAN_PAT = re.compile(
    r"\b(city|town|municipality|pourashava|metropolitan|capital|dhaka city"
    r"|urban area|ward)\b", re.I
)
_RURAL_PAT = re.compile(
    r"\b(village|para|union|rural|char|haor|beel|mauza|union parishad)\b", re.I
)

def _location_type(text: str) -> str:
    if _URBAN_PAT.search(text): return "urban"
    if _RURAL_PAT.search(text): return "rural"
    return "unknown"


# ════════════════════════════════════════════════════════════════════════════
# INCIDENT DETAILS
# ════════════════════════════════════════════════════════════════════════════

_SETTING_MAP = [
    ("madrasa",    re.compile(r"\b(madrasa|madrassa|mosque|maktab)\b", re.I)),
    ("school",     re.compile(r"\b(school|college|university|campus|classroom)\b", re.I)),
    ("workplace",  re.compile(r"\b(factory|garment|office|workplace|shop|market|farmland|farm)\b", re.I)),
    ("vehicle",    re.compile(r"\b(bus|truck|auto-?rickshaw|rickshaw|car|vehicle|microbus|boat|launch|ferry)\b", re.I)),
    ("field",      re.compile(r"\b(field|paddy\s+field|crop\s+field|open\s+field|jungle|forest|river\s+bank|canal)\b", re.I)),
    ("road",       re.compile(r"\b(road|street|highway|alley|path|footpath)\b", re.I)),
    ("home",       re.compile(r"\b(home|house|residence|room|flat|apartment|neighbor'?s?\s+house|own\s+house)\b", re.I)),
]

def _incident_setting(text: str) -> str:
    for label, pat in _SETTING_MAP:
        if pat.search(text):
            return label
    return "unknown"


_NIGHT_PAT = re.compile(
    r"\b(night|midnight|after dark|evening|dark|nocturnal|late night|last night)\b", re.I
)
_DAY_PAT = re.compile(
    r"\b(morning|afternoon|daytime|day time|broad daylight|during the day)\b", re.I
)

def _time_of_day(text: str) -> str:
    if _NIGHT_PAT.search(text): return "night"
    if _DAY_PAT.search(text):   return "day"
    return "unknown"


_METHOD_MAP = [
    ("drugged",      re.compile(r"\b(drug(?:ged)?|sedative|intoxicat|poisoned|unconscious|senseless)\b", re.I)),
    ("abducted",     re.compile(r"\b(abduct|kidnap|taken away|forcibly taken|picked up|lured away)\b", re.I)),
    ("blackmailed",  re.compile(r"\b(blackmail|threat(?:en)?|coerce|extort|video|photograph|footage)\b", re.I)),
    ("lured",        re.compile(r"\b(lured?|enticed?|false\s+promise|promise\s+of\s+marriage|tricked)\b", re.I)),
    ("forced",       re.compile(r"\b(forced?|violently|restrained|overpowered|pinned|held down)\b", re.I)),
    ("threatened",   re.compile(r"\b(threatened|intimidated|knife|weapon|gun|machete|sharp weapon)\b", re.I)),
]

def _incident_method(text: str) -> str:
    for label, pat in _METHOD_MAP:
        if pat.search(text):
            return label
    return "unknown"


_GANG_PAT = re.compile(
    r"\b(gang[\s-]?rape|gang[\s-]?assault|multiple\s+(?:men|accused|perpetrators|suspects)"
    r"|group\s+(?:rape|assault))\b", re.I
)

def _is_gang_rape(text: str) -> bool:
    return bool(_GANG_PAT.search(text))


# ════════════════════════════════════════════════════════════════════════════
# VICTIM PROFILE
# ════════════════════════════════════════════════════════════════════════════

_AGE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[\s-]year[\s-]old\b", re.I),
    re.compile(r"\baged\s+(\d{1,2})\b", re.I),
    re.compile(r"\b(\d{1,2})\s+years?\s+old\b", re.I),
    re.compile(r"\ba\s+(\d{1,2})[\s-]year\b", re.I),
    re.compile(r"\bgirl,?\s+(\d{1,2})\b", re.I),
    re.compile(r"\bwoman,?\s+(\d{1,2})\b", re.I),
]

def _extract_victim_age(text: str) -> Optional[int]:
    m = _first_match(_AGE_PATTERNS, text)
    if m:
        age = int(m.group(1))
        if 1 <= age <= 90:
            return age
    return None


def _age_group(age: Optional[int]) -> str:
    if age is None:     return "unknown"
    if age < 6:         return "infant (0-5)"
    if age < 13:        return "child (6-12)"
    if age < 18:        return "minor (13-17)"
    if age < 25:        return "young adult (18-24)"
    if age < 45:        return "adult (25-44)"
    return "older adult (45+)"


_VICTIM_COUNT_PAT = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:women|girls|victims|females|children)\b", re.I
)

def _victim_count(text: str) -> int:
    m = _VICTIM_COUNT_PAT.search(text)
    return _word_to_int(m.group(1)) if m else 1


_MALE_VICTIM_PAT = re.compile(r"\b(boy|male victim|man was raped|male child)\b", re.I)

def _victim_gender(text: str) -> str:
    if _MALE_VICTIM_PAT.search(text): return "male"
    return "female"   # overwhelmingly female in Bangladesh rape reporting


_OCCUPATION_MAP = [
    ("student",         re.compile(r"\b(student|schoolgirl|school\s+girl|college\s+girl|university\s+student|pupil)\b", re.I)),
    ("housewife",       re.compile(r"\b(housewife|homemaker|house\s*wife)\b", re.I)),
    ("garment_worker",  re.compile(r"\b(garment\s*(?:worker|employee)|rmg\s*worker|factory\s*(?:worker|girl))\b", re.I)),
    ("domestic_worker", re.compile(r"\b(domestic\s*(?:worker|help|servant)|maid|housekeeper|nanny)\b", re.I)),
    ("child",           re.compile(r"\b(child|minor|toddler|infant|girl\s*child|underage)\b", re.I)),
    ("sex_worker",      re.compile(r"\b(sex\s*worker|prostitute|brothel)\b", re.I)),
    ("day_laborer",     re.compile(r"\b(day\s*labou?rer|field\s*worker|agricultural\s*worker|farmer)\b", re.I)),
]

def _victim_occupation(text: str) -> str:
    for label, pat in _OCCUPATION_MAP:
        if pat.search(text):
            return label
    return "unknown"


_RELIGION_MAP = [
    ("hindu",     re.compile(r"\b(hindu|puja|mandir|temple|brahmin|dalit|scheduled\s+caste)\b", re.I)),
    ("christian", re.compile(r"\b(christian|church|pastor|missionary)\b", re.I)),
    ("buddhist",  re.compile(r"\b(buddhist|buddhism|pagoda|chakma|marma|tripura)\b", re.I)),
    ("muslim",    re.compile(r"\b(muslim|islam|mosque|madrasa|madrassa|namaz|salat)\b", re.I)),
]

def _victim_religion(text: str) -> str:
    for label, pat in _RELIGION_MAP.items() if hasattr(_RELIGION_MAP, 'items') else enumerate(_RELIGION_MAP):
        pass
    # use the list properly
    for label, pat in _RELIGION_MAP:
        if pat.search(text):
            return label
    return "unknown"


_MARITAL_MAP = [
    ("married",   re.compile(r"\b(wife|married\s+woman|married\s+girl|housewife|marital)\b", re.I)),
    ("unmarried", re.compile(r"\b(unmarried|single\s+woman|single\s+girl|spinster|bachelor\s*girl)\b", re.I)),
    ("widow",     re.compile(r"\b(widow|widowed|her\s+husband\s+(?:died|passed|dead))\b", re.I)),
    ("divorced",  re.compile(r"\b(divorced|divorcee|talaq|separated)\b", re.I)),
]

def _victim_marital_status(text: str) -> str:
    for label, pat in _MARITAL_MAP:
        if pat.search(text):
            return label
    return "unknown"


_DISABILITY_PAT = re.compile(
    r"\b(disabled|disability|deaf|mute|deaf-mute|mentally\s+(?:ill|challenged|disabled)"
    r"|special\s+needs|speech\s+impaired|physically\s+challenged)\b", re.I
)

def _victim_disability(text: str) -> int:
    return int(bool(_DISABILITY_PAT.search(text)))


_KNEW_PERP_PAT = re.compile(
    r"\b(known\s+to\s+(?:the\s+)?victim|victim\s+knew|familiar|acquaintance"
    r"|neighbor|neighbour|teacher|relative|uncle|employer|colleague|classmate"
    r"|boyfriend|husband|guardian)\b", re.I
)
_STRANGER_PAT = re.compile(r"\b(stranger|unknown\s+(?:man|person|assailant)|unidentified)\b", re.I)

def _knew_perpetrator(text: str) -> Optional[int]:
    if _KNEW_PERP_PAT.search(text): return 1
    if _STRANGER_PAT.search(text):  return 0
    return None


_KILLED_AFTER_PAT = re.compile(
    r"\b(killed\s+(?:after|following|the)\s+(?:rape|assault|attack)"
    r"|murder(?:ed)?\s+(?:after|following|the)\s+(?:rape|assault)"
    r"|raped\s+and\s+(?:then\s+)?killed|raped\s+and\s+(?:then\s+)?murdered"
    r"|body\s+found\s+after|found\s+dead\s+after\s+(?:rape|assault))\b", re.I
)

def _victim_killed_after(text: str) -> int:
    return int(bool(_KILLED_AFTER_PAT.search(text)))


_SUICIDE_PAT = re.compile(
    r"\b(suicide|took\s+(?:her|his|their)\s+(?:own\s+)?life|hang(?:ed)?\s+(?:her|him)self"
    r"|killed\s+(?:her|him)self|self-harm|self\s+harm|died\s+(?:by|of)\s+suicide)\b", re.I
)

def _victim_suicide(text: str) -> int:
    return int(bool(_SUICIDE_PAT.search(text)))


# ════════════════════════════════════════════════════════════════════════════
# PERPETRATOR PROFILE
# ════════════════════════════════════════════════════════════════════════════

# Separate age patterns for perpetrator — look after "accused", "perpetrator", "rapist" etc.
_PERP_AGE_PATTERNS = [
    re.compile(r"(?:accused|suspect|perpetrator|rapist|man|attacker),?\s+(\d{1,2})\b", re.I),
    re.compile(r"\b(\d{1,2})[\s-]year[\s-]old\s+(?:man|youth|boy|accused)\b", re.I),
    re.compile(r"\baged\s+(\d{1,2})\s+(?:years?)?\s*,?\s+(?:a|the)?\s*(?:man|youth|accused)\b", re.I),
]

def _perp_age(text: str) -> Optional[int]:
    m = _first_match(_PERP_AGE_PATTERNS, text)
    if m:
        age = int(m.group(1))
        if 10 <= age <= 90:
            return age
    return None


_PERP_COUNT_PAT = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:men|boys|accused|suspects|perpetrators|youths|persons)\b", re.I
)

def _perp_count(text: str, gang: bool) -> int:
    m = _PERP_COUNT_PAT.search(text)
    if m:
        return _word_to_int(m.group(1))
    return 2 if gang else 1


_PERP_OCCUPATION_MAP = [
    ("teacher",           re.compile(r"\b(teacher|madrasa\s+teacher|school\s+teacher|tutor|instructor|headmaster)\b", re.I)),
    ("religious_leader",  re.compile(r"\b(imam|moulana|maulana|hujur|cleric|qazi|religious\s+leader)\b", re.I)),
    ("political_worker",  re.compile(r"\b((?:awami\s+league|bnp|jatiya\s+party|jamaat|political\s+worker"
                                      r"|party\s+(?:worker|leader|activist)|union\s+(?:member|chairman|parishad\s+member)"
                                      r"|ward\s+(?:councilor|councillor)|upazila\s+(?:chairman|member)))\b", re.I)),
    ("police",            re.compile(r"\b(police(?:man)?|constable|sub-?inspector|officer\s+in\s+charge|oc|asp|si)\b", re.I)),
    ("army_paramilitary", re.compile(r"\b(soldier|army|military|rab|ansar|border\s+guard|bgb)\b", re.I)),
    ("businessman",       re.compile(r"\b(businessman|merchant|shopkeeper|trader|owner)\b", re.I)),
    ("student",           re.compile(r"\b(student\s+(?:accused|perpetrator|suspect)|student\s+(?:of|at)\s+\w+\s+(?:school|college))\b", re.I)),
    ("laborer",           re.compile(r"\b(labou?rer|day\s*labou?rer|construction\s*worker|rickshaw\s*(?:puller|driver))\b", re.I)),
    ("driver",            re.compile(r"\b(driver|bus\s*driver|truck\s*driver|auto\s*driver|van\s*driver)\b", re.I)),
]

def _perp_occupation(text: str) -> str:
    for label, pat in _PERP_OCCUPATION_MAP:
        if pat.search(text):
            return label
    return "unknown"


def _perp_relationship(text: str) -> Optional[str]:
    text_lower = text.lower()
    for ptype, keywords in PERPETRATOR_TYPES.items():
        for kw in keywords:
            if kw in text_lower:
                return ptype
    return None


_POLITICAL_CON_PAT = re.compile(
    r"\b(ruling\s+party|political\s+(?:connection|link|backing|shelter|protection)"
    r"|politically\s+(?:connected|influential|powerful|backed)"
    r"|(?:awami\s+league|bnp|jamaat)\s+(?:leader|worker|activist|member)"
    r"|local\s+(?:mp|minister|chairman)\s+(?:backed|linked|connected))\b", re.I
)

def _political_connection(text: str) -> int:
    return int(bool(_POLITICAL_CON_PAT.search(text)))


_PRIOR_RECORD_PAT = re.compile(
    r"\b(previous(?:ly)?\s+(?:convicted|arrested|accused|charged)|prior\s+(?:case|offence|offense|criminal\s+record)"
    r"|prior\s+criminal|criminal\s+record|repeat\s+offender|serial\s+(?:rapist|offender)"
    r"|habitual\s+offender|accused\s+before|history\s+of\s+(?:crime|assault|violence))\b", re.I
)

def _prior_record(text: str) -> int:
    return int(bool(_PRIOR_RECORD_PAT.search(text)))


_WEAPON_PAT = re.compile(
    r"\b(knife|blade|sharp\s+weapon|machete|dao|rod|stick|firearm|pistol|gun"
    r"|threatened\s+with|armed\s+with|at\s+knifepoint|at\s+gunpoint)\b", re.I
)

def _used_weapon(text: str) -> int:
    return int(bool(_WEAPON_PAT.search(text)))


_INTOXICANT_PAT = re.compile(
    r"\b(drug(?:ged)?|sedative|sleeping\s+(?:pill|tablet)|mixed\s+in\s+(?:food|drink|water)"
    r"|unconscious(?:\s+after)?|intoxicat|alcohol|drunk|under\s+the\s+influence)\b", re.I
)

def _used_intoxicant(text: str) -> int:
    return int(bool(_INTOXICANT_PAT.search(text)))


_LOCAL_INFLUENCE_PAT = re.compile(
    r"\b(influential|powerful|local\s+(?:influential|strongman|muscle\s+man|goon)"
    r"|backed\s+by|sheltered\s+by|no\s+one\s+(?:dared|could\s+stop)|went\s+unpunished"
    r"|intimidated\s+(?:family|victim|witness)|pressure\s+(?:on|applied))\b", re.I
)

def _local_influence(text: str) -> int:
    return int(bool(_LOCAL_INFLUENCE_PAT.search(text)))


# ════════════════════════════════════════════════════════════════════════════
# PSYCHOLOGICAL INDICATORS
# ════════════════════════════════════════════════════════════════════════════

_POWER_MOTIVE_PAT = re.compile(
    r"\b(abused?\s+(?:his\s+)?(?:position|authority|power|trust)|took\s+advantage\s+of"
    r"|exploited\s+(?:his\s+)?(?:position|authority)|guardian|trusted|in\s+(?:his\s+)?care"
    r"|teacher-student|employer-employee|in\s+(?:his\s+)?custody)\b", re.I
)

def _power_motive(text: str) -> int:
    return int(bool(_POWER_MOTIVE_PAT.search(text)))


_OPPORTUNISTIC_PAT = re.compile(
    r"\b(found\s+(?:her\s+)?alone|was\s+alone|home\s+alone|no\s+one\s+(?:was\s+)?around"
    r"|parents?\s+(?:were\s+)?(?:not\s+)?(?:home|present|away)|taking\s+advantage"
    r"|opportunity|opportunistic)\b", re.I
)

def _opportunistic(text: str) -> int:
    return int(bool(_OPPORTUNISTIC_PAT.search(text)))


_PREMEDITATED_PAT = re.compile(
    r"\b(planned|premeditated|lured|waited\s+for|followed\s+(?:her|the\s+victim)"
    r"|stalked?|prepared|plotted|conspired|agreed\s+(?:to|among)|called\s+(?:her\s+)?to"
    r"|invited\s+(?:on\s+false\s+)?pretext)\b", re.I
)

def _premeditated(text: str) -> int:
    return int(bool(_PREMEDITATED_PAT.search(text)))


_REVENGE_PAT = re.compile(
    r"\b(revenge|retaliation|grudge|due\s+to\s+(?:dispute|enmity|feud)"
    r"|land\s+dispute|family\s+feud|enmity|personal\s+(?:grudge|feud|dispute)"
    r"|rejected|refused\s+(?:his\s+)?(?:proposal|love|advances))\b", re.I
)

def _revenge_motive(text: str) -> int:
    return int(bool(_REVENGE_PAT.search(text)))


# ════════════════════════════════════════════════════════════════════════════
# JUSTICE / OUTCOME
# ════════════════════════════════════════════════════════════════════════════

_CASE_FILED_PAT = re.compile(
    r"\b(case\s+(?:was\s+\w+\s+)?filed|case\s+(?:was\s+)?filed|fir\s+(?:was\s+)?lodged"
    r"|filed\s+a\s+case|lodged\s+a\s+case|complaint\s+(?:was\s+\w+\s+)?filed"
    r"|police\s+case|filed\s+with\s+police|filed\s+under|filed\s+a\s+(?:rape|assault)\s+case)\b", re.I
)

def _case_filed(text: str) -> int:
    return int(bool(_CASE_FILED_PAT.search(text)))


_ARREST_PAT = re.compile(
    r"\b(arrested|detained|held|in\s+custody|remanded|nabbed|apprehended|caught)\b", re.I
)

def _arrest_made(text: str) -> int:
    return int(bool(_ARREST_PAT.search(text)))


_TRIAL_PAT = re.compile(
    r"\b(trial|charge\s*sheet|chargesheet|tribunal|court\s+proceedings|hearing"
    r"|produced\s+before\s+(?:a\s+)?court|sent\s+to\s+(?:jail|prison)|nari\s+o\s+shishu)\b", re.I
)

def _trial_mentioned(text: str) -> int:
    return int(bool(_TRIAL_PAT.search(text)))


_CONVICTION_PAT = re.compile(
    r"\b(convicted|conviction|sentenced|death\s+penalty|life\s+imprisonment"
    r"|years?\s+(?:in\s+)?(?:jail|prison)|found\s+guilty|verdict)\b", re.I
)

def _conviction_mentioned(text: str) -> int:
    return int(bool(_CONVICTION_PAT.search(text)))


_INCIDENT_DATE_PAT = re.compile(
    r"\bon\s+(\w+\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}\s+\w+(?:\s+\d{4})?)\b", re.I
)

def _incident_date(text: str) -> Optional[str]:
    m = _INCIDENT_DATE_PAT.search(text)
    return m.group(1).strip() if m else None


# ════════════════════════════════════════════════════════════════════════════
# KEYWORDS
# ════════════════════════════════════════════════════════════════════════════

_KW_LIST = [
    "rape", "gang rape", "sexual assault", "minor", "child", "student",
    "teacher", "madrasa", "neighbor", "relative", "arrested", "case filed",
    "killed", "suicide", "political", "police", "weapon", "drugged",
    "blackmail", "influential",
]

def _keywords(text: str) -> str:
    tl = text.lower()
    return json.dumps([k for k in _KW_LIST if k in tl])


# ════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

def extract_case(article_row) -> Optional[dict]:
    content   = article_row["content"] or ""
    title     = article_row["title"]   or ""
    full_text = f"{title} {content}"

    if not re.search(r"\brap(?:e[ds]?|ing)\b|\bgang[\s-]?rape\b|\bsexual\s+assault\b", full_text, re.I):
        return None

    gang         = _is_gang_rape(full_text)
    victim_age   = _extract_victim_age(full_text)
    perp_age_val = _perp_age(full_text)

    return {
        # meta
        "article_id":              article_row["id"],
        "source":                  article_row["source"],
        "article_url":             article_row["url"],
        "article_title":           title,
        "published_date":          article_row["published_date"],
        "incident_date":           _incident_date(full_text),

        # location
        "district":                _extract_district(full_text),
        "upazila":                 _extract_upazila(full_text),
        "location_type":           _location_type(full_text),

        # incident
        "incident_setting":        _incident_setting(full_text),
        "incident_time_of_day":    _time_of_day(full_text),
        "incident_method":         _incident_method(full_text),
        "gang_rape":               int(gang),

        # victim profile
        "victim_count":            _victim_count(full_text),
        "victim_age":              victim_age,
        "victim_age_group":        _age_group(victim_age),
        "victim_gender":           _victim_gender(full_text),
        "victim_occupation":       _victim_occupation(full_text),
        "victim_religion":         _victim_religion(full_text),
        "victim_marital_status":   _victim_marital_status(full_text),
        "victim_disability":       _victim_disability(full_text),
        "victim_knew_perpetrator": _knew_perpetrator(full_text),
        "victim_killed_after":     _victim_killed_after(full_text),
        "victim_suicide":          _victim_suicide(full_text),

        # perpetrator profile
        "perpetrator_count":       _perp_count(full_text, gang),
        "perp_age":                perp_age_val,
        "perp_age_group":          _age_group(perp_age_val),
        "perp_gender":             "male",
        "perp_occupation":         _perp_occupation(full_text),
        "perp_relationship":       _perp_relationship(full_text),
        "perp_political_connection": _political_connection(full_text),
        "perp_prior_record":       _prior_record(full_text),
        "perp_used_weapon":        _used_weapon(full_text),
        "perp_used_intoxicant":    _used_intoxicant(full_text),
        "perp_local_influence":    _local_influence(full_text),

        # psychological
        "psych_power_motive":      _power_motive(full_text),
        "psych_opportunistic":     _opportunistic(full_text),
        "psych_premeditated":      _premeditated(full_text),
        "psych_revenge_motive":    _revenge_motive(full_text),

        # justice
        "case_filed":              _case_filed(full_text),
        "arrest_made":             _arrest_made(full_text),
        "trial_mentioned":         _trial_mentioned(full_text),
        "conviction_mentioned":    _conviction_mentioned(full_text),

        "keywords_matched":        _keywords(full_text),
    }
