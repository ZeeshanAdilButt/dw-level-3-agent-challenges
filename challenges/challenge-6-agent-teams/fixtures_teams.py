"""Fixed fixtures for the lab 6 tests: fixture principals, a scripted model, and an agent built on the stub.

Nothing here calls a network or a real model, and no test compares against a reference number.
"""
from __future__ import annotations

import itertools
import os
import sys
import threading
from pathlib import Path

os.environ["DW_MODEL_PATH"] = "stub"
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import Agent  # noqa: E402
from app.model import ChatResult, ModelClient  # noqa: E402
from app.settings import validate  # noqa: E402
from app.types import Message, Principal  # noqa: E402
from mock_api import MockClient  # noqa: E402

PACKS = ROOT / "packs"
PROSPECT = Principal("prospect-01", "prospect", False, None)
ANA = Principal("acct-1001-owner", "customer", True, "acct-1001")       # a Quillon customer in the fixture
PATIENT = Principal("acct-5001-owner", "customer", True, "acct-5001")   # a Juniper Lane Clinic patient in the fixture

_ids = itertools.count(1)


def msg(text: str, principal: Principal = PROSPECT, conv: str = "c1") -> Message:
    return Message(f"r{next(_ids)}", conv, principal, text)


class Scripted(ModelClient):
    """Answers from a script (a string, a dict {"text", "tool_calls"}, or a callable), then falls back to the stub.
    Records every call it receives, so a test can read exactly what each team member was shown."""

    def __init__(self, settings: dict, replies=()):
        super().__init__(settings)
        self.replies = list(replies)
        self.calls: list[dict] = []
        self._lock = threading.Lock()

    def chat(self, messages, tools, span_name, tracer):
        with tracer.span("model", step=span_name) as sp:
            tracer.next_call()
            with self._lock:
                self.calls.append({"messages": [dict(m) for m in messages], "tools": tools, "step": span_name})
                scripted = self.replies.pop(0) if self.replies else None
            if callable(scripted):
                scripted = scripted(messages, tools, span_name)
            if scripted is None:
                res = self._stub(messages, tools, span_name)
            else:
                d = scripted if isinstance(scripted, dict) else {"text": scripted}
                calls = [{"id": f"s-{i}", "name": c["name"], "arguments": c.get("arguments", {})}
                         for i, c in enumerate(d.get("tool_calls", []))]
                res = ChatResult(text=d.get("text", ""), tool_calls=calls, tokens_in=10, tokens_out=5, model="stub")
            sp.model, sp.tokens_in, sp.tokens_out = res.model, res.tokens_in, res.tokens_out
        return res


def make_agent(pack: str = "quillon", replies=(), **settings) -> Agent:
    s = validate({"pack": pack, "model_path": "stub", **settings})
    pack_dir = PACKS / pack
    return Agent(s, pack_dir, MockClient(pack_dir, "test"), Scripted(s, replies))
