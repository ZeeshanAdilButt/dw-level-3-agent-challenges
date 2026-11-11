"""Saltmarsh Mutual's hard rules as code: no payout promise, identity before any policy or claim detail,
conflicts between documents settled by authority (the authority rule is forced on), else a handoff."""
from __future__ import annotations

import re

from .common import Decision, POLICY_NUMBER, parse_dates

PROMISE_ASK = re.compile(r"\b(promise|guarantee|assure|definitely|confirm|swear)\b.{0,90}\b(pay|paid|payout|approve|approved|settle|settled|covered|reimburse\w*)\b|"
                         r"\bmoney (is|will be) (on its way|coming)\b|\bi am covered and the money\b", re.I)
PERSONAL = re.compile(r"\b(what|when|which|tell me|show|give me|check|how much)\b[^.?!]*\b(my|our)\b[^.?!]*\b(excess|renewal|riders?|premium|policy|cover(age)?|claim|limit|sum insured|start date)\b|"
                      r"\b(what|which|how many)\b[^.?!]*\b(riders?|policies|claims)\b[^.?!]*\b(do i have|have i got|do we have)\b|"
                      r"\bclaim status\b|\bCLM-\d{2}-\d{4}\b", re.I)
OPEN_CLAIM = re.compile(r"\b(open|start|make|file|lodge|register|submit|raise)\b.{0,30}\bclaim\b", re.I)
PAY_WORDING = [
    re.compile(r"\byou('| a)?re (fully )?covered\b|\byou are (fully )?covered\b", re.I),
    re.compile(r"\bwill (definitely |certainly |surely )?be (paid|approved|settled|accepted|covered)\b", re.I),
    re.compile(r"\b(claim|it) (is|has been|was) approved\b", re.I),
    re.compile(r"\bmoney (is|will be) (coming|on its way|paid)\b", re.I),
    re.compile(r"\bwe('ll| will) (definitely |certainly )?(pay|cover|settle|reimburse)\b", re.I),
    re.compile(r"\byou will (definitely |certainly )?(receive|get) (a |the |your )?(payout|payment|settlement|money)\b", re.I),
    re.compile(r"\bguarantee[sd]? (a |the )?(payout|payment|settlement|outcome)\b", re.I),
]
NEG = re.compile(r"(not|n't|cannot|never|no|unable|without|can't|won't)\b[^.]{0,40}$", re.I)
CLAUSE = re.compile(r"[,;:]|\b(?:so|but|and|yet|because|however|although|though)\b", re.I)   # a negation reaches only its own clause


class SaltmarshRules:
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
