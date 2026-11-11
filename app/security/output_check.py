"""The leak check on a reply before it is sent: system prompt word runs, PII patterns, and text of items the principal
may not see (found by searching the index without the access check)."""
from __future__ import annotations

import re

from ..rules.common import parse_dates
from . import pii
from .access import allowed, item_for_doc

RUN_WORDS = 7           # a run of this many words copied from the system prompt, or from a document, is a leak


def _words(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


def _runs(words: list[str], source_words: list[str], n: int) -> set:
    """The runs of n words that the text and the source share."""
    if len(words) < n or len(source_words) < n:
        return set()
    grams = {tuple(source_words[i:i + n]) for i in range(len(source_words) - n + 1)}
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)} & grams


def _has_run(words: list[str], source_words: list[str], n: int) -> bool:
    return bool(_runs(words, source_words, n))


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(_words(s)) >= 5]


def leak_check(reply: str, *, system_prompt: str, principal, index, own_text: str = "") -> list[str]:
    """Starter: finds no leak. Lab 7 part 2 compares the reply with what the principal may not see."""
    return []
