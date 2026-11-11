"""The router: one model call that picks one or two areas and writes a note for each specialist.
The principal is passed by the core and never inside a note: the router never sees it, and ids are stripped from its notes."""
from __future__ import annotations

from ..prompts import fill, text
from ..security import pii
from .base import Turn, first_json
from .specialists import AREAS


def route(core, turn: Turn) -> list[dict]:
    raise NotImplementedError("YOUR TURN: lab 6 part 1, the router")
