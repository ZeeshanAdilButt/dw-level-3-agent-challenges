"""Shared test data and helpers for the app tests (not a conftest, so it cannot collide with tests/ui). Everything runs on the stub model: no network, no Ollama."""
from __future__ import annotations

import itertools
import threading
from pathlib import Path

from app.core import Agent
from app.model import ChatResult, ModelClient
from app.settings import validate
from app.types import Message, Principal
from mock_api import MockClient

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / "packs"

PROSPECT = Principal("prospect-01", "prospect", False, None)
ANA = Principal("acct-1001-owner", "customer", True, "acct-1001")       # Ashgrove Legal
BEN = Principal("acct-1004-owner", "customer", True, "acct-1004")       # Delmar Treasury
CAT = Principal("acct-1005-owner", "customer", True, "acct-1005")       # Eastfield & Rowe
STAFF = Principal("staff-01", "staff", True, None)
PATIENT = Principal("acct-5001-owner", "customer", True, "acct-5001")   # owns pt-2001, adult, CF-12 complete
PATIENT_7 = Principal("acct-5007-owner", "customer", True, "acct-5007")  # owns pt-2008
PARENT = Principal("acct-5002-owner", "customer", True, "acct-5002")    # owns pt-2002 and pt-2003
ELEANOR = Principal("ph-3001-owner", "customer", True, "ph-3001")       # SM-H-100231, born 1981-03-14
RASHID = Principal("ph-3002-owner", "customer", True, "ph-3002")        # SM-H-100232, born 1975-11-02

_ids = itertools.count(1)


def msg(text: str, principal: Principal = PROSPECT, conv: str = "c1", rid: str | None = None) -> Message:
    return Message(rid or f"r{next(_ids)}", conv, principal, text)


class Scripted(ModelClient):
    """A model that answers from a script, then falls back to the stub. Each reply is a string, a dict
    {"text", "tool_calls"} or a callable (messages, tools, step) -> either. Records every call it receives."""

    def __init__(self, settings: dict, replies=(), gate: threading.Event | None = None, entered: threading.Event | None = None):
        super().__init__(settings)
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.gate, self.entered = gate, entered
        self._lock = threading.Lock()

    def chat(self, messages, tools, span_name, tracer):
        with tracer.span("model", step=span_name) as sp:
            tracer.next_call()
            with self._lock:
                self.calls.append({"messages": [dict(m) for m in messages], "tools": tools, "step": span_name})
                nxt = self.replies[0] if self.replies else None
                is_cls = isinstance(nxt, str) and nxt.lstrip().startswith('{"category"')
                scripted = self.replies.pop(0) if self.replies and (span_name != "classifier" or is_cls) else None
            if self.entered:
                self.entered.set()
            if self.gate:
                self.gate.wait(5)
            if callable(scripted):
                scripted = scripted(messages, tools, span_name)
            if scripted is None:
                res = self._stub(messages, tools, span_name)
            else:
                d = scripted if isinstance(scripted, dict) else {"text": scripted}
                calls = [{"id": f"s-{i}", "name": c["name"], "arguments": c.get("arguments", {})} for i, c in enumerate(d.get("tool_calls", []))]
                res = ChatResult(text=d.get("text", ""), tool_calls=calls, tokens_in=10, tokens_out=5, model="stub")
            sp.model, sp.tokens_in, sp.tokens_out = res.model, res.tokens_in, res.tokens_out
        return res


def make_agent(pack: str = "quillon", replies=(), pack_dir: Path | None = None, **settings) -> Agent:
    s = validate({"pack": pack, "model_path": "stub", **settings})
    pd = pack_dir or PACKS / pack
    model = Scripted(s, replies)
    return Agent(s, pd, MockClient(pd, "test"), model)
