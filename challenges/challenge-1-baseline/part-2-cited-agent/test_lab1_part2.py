"""Lab 1, part 2: a cited agent. Every test uses a scripted stand-in for the model: no network, no Ollama.

Invariant (passes on the starter): test_core_has_no_channel_code, test_health.
Acceptance (fails on the starter): test_cited_answer, test_repeat_request_id, test_history_is_per_principal. The first fails with
    AssertionError: expected a citation, the starter core answered "I don't know yet"
"""
import ast
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["DW_MODEL_PATH"] = "stub"

from app.core import Agent  # noqa: E402
from app.model import ChatResult, ModelClient  # noqa: E402
from app.settings import validate  # noqa: E402
from app.types import Message, Principal  # noqa: E402
from mock_api import MockClient  # noqa: E402

PACK = ROOT / "packs" / "quillon"
ANA = Principal("acct-1001-owner", "customer", True, "acct-1001")
BEN = Principal("acct-1004-owner", "customer", True, "acct-1004")
QUESTION = "How much is Pro per seat if we pay every month?"
DOC_LINE = re.compile(r"^\[(doc-[\w\-]+)\] ", re.M)


class ScriptedModel(ModelClient):
    """Cites the first document it was given, plus one document id that was never delivered. Records every call."""

    def __init__(self, settings):
        super().__init__(settings)
        self.calls = []
        self.given = []

    def chat(self, messages, tools, span_name, tracer):
        self.calls.append([dict(m) for m in messages])
        user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        ids = DOC_LINE.findall(user)
        self.given.append(ids)
        cite = f"[{ids[0]}] " if ids else ""
        text = f"The Pro plan is priced per seat. {cite}It is also in [doc-never-delivered]."
        with tracer.span("model", step=span_name) as sp:
            res = ChatResult(text=text, tool_calls=[], tokens_in=10, tokens_out=5, model="stub")
            sp.model, sp.tokens_in, sp.tokens_out = "stub", 10, 5
        return res


def make_agent():
    settings = validate({"pack": "quillon", "model_path": "stub"})
    return Agent(settings, PACK, MockClient(PACK, "part2"), ScriptedModel(settings))


def msg(text, principal=ANA, conv="c-7", rid="req-1"):
    return Message(rid, conv, principal, text)


# ---- invariant ---------------------------------------------------------------------------------------------------

def test_core_has_no_channel_code():
    tree = ast.parse((ROOT / "app" / "core.py").read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if "adapters" in mod.split(".") or any(a.name == "adapters" for a in node.names):
                bad.append(mod or "adapters")
        elif isinstance(node, ast.Import):
            bad += [a.name for a in node.names if "adapters" in a.name.split(".")]
    assert not bad, f"app/core.py imports channel code: {bad}"


def test_health():
    from fastapi.testclient import TestClient
    from app.adapters.chat import create_app
    with tempfile.TemporaryDirectory() as tmp:
        client = TestClient(create_app(root=ROOT, runs_dir=Path(tmp), agent_factory=lambda: object()))
        body = client.get("/health").json()
    assert body["status"] == "ok"


# ---- acceptance --------------------------------------------------------------------------------------------------

def test_cited_answer():
    agent = make_agent()
    reply = agent.handle(msg(QUESTION))
    assert reply.citations, f'expected a citation, the starter core answered "{reply.text}"'
    delivered = agent.model.given[0]
    assert delivered, "the model was given no documents: retrieval did not reach the prompt"
    assert reply.citations == [delivered[0]]                      # the delivered document is kept
    assert "doc-never-delivered" not in reply.citations           # a document the model never saw is dropped
    assert set(reply.citations) <= set(reply.eval.delivered_doc_ids)
    assert reply.eval.ranked_hit_ids and reply.eval.raw_reply == reply.text
    assert reply.latency_ms >= 0 and reply.trace_id


def test_repeat_request_id():
    agent = make_agent()
    first = agent.handle(msg(QUESTION, rid="same-id"))
    calls = len(agent.model.calls)
    again = agent.handle(msg(QUESTION, rid="same-id"))
    assert again.text == first.text and again.trace_id == first.trace_id
    assert len(agent.model.calls) == calls, "a repeated request id must return the stored reply with no second model call"
    other = agent.handle(msg(QUESTION, principal=BEN, rid="same-id"))
    assert len(agent.model.calls) == calls + 1, "the same request id from another principal must not get a stored reply"
    assert other.trace_id != first.trace_id


def test_history_is_per_principal():
    earlier = "What is the uptime commitment?"
    agent = make_agent()
    agent.handle(msg(earlier, principal=ANA, conv="c-7", rid="a1"))
    agent.handle(msg(QUESTION, principal=BEN, conv="c-7", rid="b1"))
    assert not any(m["role"] == "user" and m["content"] == earlier for m in agent.model.calls[-1]),         "another principal's history reached this principal"
    agent.handle(msg("And for the Team plan?", principal=ANA, conv="c-7", rid="a2"))
    assert any(m["role"] == "user" and m["content"] == earlier for m in agent.model.calls[-1]),         "the same principal in the same conversation should have its history"
