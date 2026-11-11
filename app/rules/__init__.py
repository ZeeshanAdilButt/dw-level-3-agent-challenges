"""The rules layer: each company's hard rules as code, run before the model and again on the reply after it.

`make_rules(pack, fixture, settings)` returns the company's rule object. `check_claimed_action` is the one check every
company shares: a reply must not say something was booked, created or opened when the mock holds no such action.
"""
from __future__ import annotations

import re

from .common import Decision  # noqa: F401
from .juniper import JuniperRules
from .quillon import QuillonRules
from .saltmarsh import SaltmarshRules

_RULES = {"quillon": QuillonRules, "juniper": JuniperRules, "saltmarsh": SaltmarshRules}

CLAIMS_DONE = re.compile(
    r"\b(i('ve| have)|we('ve| have)|you('re| are)( now)?|has been|have been|is now|are now|was)\s+(booked|scheduled|confirmed|created|opened|placed|reserved|registered|set up)\b|"
    r"\b(booking|appointment|demo|quote|claim)\s+(is |has been |was )?(confirmed|booked|created|opened|made)\b", re.I)
STATE_TOOLS = {"create_quote", "book_demo", "book_appointment", "open_claim"}


def make_rules(pack: str, fixture: dict, settings: dict):
    return _RULES[pack](fixture, settings)


def check_claimed_action(text: str, attempted: list, executed: list) -> Decision | None:
    raise NotImplementedError("YOUR TURN: lab 5 part 2, the reply rules check and the handoff line")


def parse_handoff_line(text: str) -> tuple[str, dict | None]:
    raise NotImplementedError("YOUR TURN: lab 5 part 2, the reply rules check and the handoff line")
