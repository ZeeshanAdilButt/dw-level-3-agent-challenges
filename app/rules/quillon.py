"""Quillon's hard rules as code: prices only from the quote tool or the price table, the 10 percent discount line,
no 'agree to everything', clarify before an underspecified request."""
from __future__ import annotations

import re

from .common import Decision, EMAIL, parse_discount, parse_quote_request

AGREE = re.compile(r"(yes to everything|answer ['\"]?agreed|agree to (all|everything)|agree with everything|"
                   r"confirm now that you agree|you agree to all|say yes to all)", re.I)
MONEY = re.compile(r"(?:[$€£]|USD\s|EUR\s)\s?(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*(?:dollars|euros|usd|eur)\b", re.I)
PLAN_RX = re.compile(r"\b(starter|team|pro|enterprise)\b", re.I)


class QuillonRules:
    """Starter: no hard rules. Lab 5 part 2 writes them (before the model, after the model, the classifier categories)."""
    uses_classifier = False
    force_authority = False

    def __init__(self, fixture: dict, settings: dict):
        self.fixture = fixture
        self.settings = settings

    def before(self, msg, state, tools_on: bool):
        return None

    def classify_category(self, category: str, msg, state, tools_on: bool):
        return None

    def after(self, text: str, ctx: dict):
        return None
