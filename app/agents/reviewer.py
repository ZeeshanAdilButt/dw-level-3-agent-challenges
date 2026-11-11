"""The reviewer: sees the question, the draft, its citations and what was delivered. It passes, or asks for one revision, never more."""
from __future__ import annotations

from ..prompts import text
from .base import Turn, first_json


def review(core, turn: Turn, draft: str, cited: list, delivered: list) -> dict:
    raise NotImplementedError("YOUR TURN: lab 6 part 2, the reviewer")
