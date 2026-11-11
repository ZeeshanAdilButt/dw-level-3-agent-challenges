"""Shared pieces of the rules layer: the decision type, small parsers, and message patterns."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Decision:
    """What a rule decided. `action`: refuse | handoff | clarify | emergency | rewrite."""
    action: str
    text: str
    hit: str
    handoff: dict | None = None
    pending: str | None = None
    attempts: list = field(default_factory=list)     # tool calls the core makes first, so the attempt is recorded
    tool: str | None = None                          # a clarify asked for this action tool: the answer counts as asking for it


MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})


def parse_dates(text: str) -> list[str]:
    """ISO dates found in free text: 14 March 1981, March 14 1981, 1981-03-14, 14/03/1981 (day first)."""
    out = []
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        out.append(m.group(0))
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b", text):
        mon = MONTHS.get(m.group(2).lower())
        if mon:
            out.append(_iso(m.group(3), mon, m.group(1)))
    for m in re.finditer(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", text):
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            out.append(_iso(m.group(3), mon, m.group(2)))
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text):
        out.append(_iso(m.group(3), m.group(2), m.group(1)))
    return [d for d in out if d]


def _iso(y, mo, d):
    try:
        return date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None


def parse_day_in_text(text: str, year: int = 2026) -> list[str]:
    """Dates written without a year, such as 'on 4 November' or 'since 3 November'."""
    out = []
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\b(?!\s*,?\s*\d{4})", text):
        mon = MONTHS.get(m.group(2).lower())
        if mon:
            out.append(_iso(year, mon, m.group(1)))
    return [d for d in out if d]


POLICY_NUMBER = re.compile(r"\bSM-[HM]-\d{6}\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

PLAN_WORDS = {"starter": "PLN-STR-10", "team": "PLN-TEAM-25", "pro": "PLN-PRO-50", "enterprise": "PLN-ENT-200"}


def parse_quote_request(text: str) -> dict:
    """Whatever a quote request states: plan code, seats, term, discount_pct. Missing parts are left out."""
    low = text.lower()
    out: dict = {}
    for word, code in PLAN_WORDS.items():
        if re.search(rf"\b{word}\b", low):
            out["plan"] = code
            break
    m = re.search(r"\b(\d{1,4})\s+(?:[a-z]+\s+)?seats?\b", low)
    if m:
        out["seats"] = int(m.group(1))
    if re.search(r"\b(annual|annually|yearly|a year|per year|12 months|for the year|for a year)\b", low):
        out["term"] = "annual"
    elif re.search(r"\b(monthly|per month|every month|each month|month by month|month-to-month)\b", low):
        out["term"] = "monthly"
    pct = parse_discount(text)
    out["discount_pct"] = pct if pct is not None else 0
    return out


_DISC = [
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)\s*(?:off|discount|reduction|rebate|cheaper|less)", re.I),
    re.compile(r"(?:discount|off|reduction|rebate|waive|waiver)\s*(?:of|by|to)?\s*(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)", re.I),
    re.compile(r"(?:give|get|take|knock|put|apply|want|need|add|is fine|fine)\s+(?:us\s+|me\s+)?(?:a\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)\s+(?:on|is fine|is ok|is okay)\b", re.I),
]


def parse_discount(text: str) -> float | None:
    for rx in _DISC:
        m = rx.search(text)
        if m:
            v = float(m.group(1))
            return int(v) if v == int(v) else v
    return None


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def normalise_words(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


AFFIRM = re.compile(r"^\s*(yes|yep|yeah|sure|ok|okay|confirm|confirmed|go ahead|please do|do it|that is right|that's right|correct)\b", re.I)
NEGATE = re.compile(r"^\s*(no|nope|cancel|stop|don't|do not|never mind|nevermind)\b", re.I)
_WANT = r"i'?d like|i would like|i want|i need|can i have|can i get|put me down for|put us down for|sign me up for"
_APPOINTMENT = (r"appointment|slot|consult\w*|test|check|procedure|call|visit|screening|vaccination|jab|assessment|follow-?up|"
                r"physio\w*|bloods?|gp|session|smear")
# An explicit request names the action: a verb of asking plus the thing the tool makes. Politeness ("please", "can you")
# alone is not a request for an action.
ACTION_REQUEST = {
    "book_demo": re.compile(rf"\b(book|schedule|reserve|arrange|set up|take|grab|{_WANT})\b.{{0,60}}\bdemo\b", re.I),
    "create_quote": re.compile(rf"\bquote (me|us|for|\d)|^\s*quote\b|\b(create|get|give|send|make|prepare|issue|draw up|put|{_WANT})\b"
                               r".{0,40}\bquote\b", re.I),
    "book_appointment": re.compile(rf"\b(book|rebook|schedule|reserve|arrange|{_WANT})\b.{{0,60}}\b({_APPOINTMENT})\b|"
                                   r"\bbook (me|us|him|her|them) in\b", re.I),
    "open_claim": re.compile(r"\b(open|file|start|make|lodge|submit|raise|register|log)\b.{0,30}\bclaim\b", re.I),
}


def explicit_request(tool: str, text: str) -> bool:
    """Did the message itself ask for this action (book a demo, create a quote, book an appointment, open a claim)?"""
    rx = ACTION_REQUEST.get(tool)
    return bool(rx and rx.search(text or ""))
