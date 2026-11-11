"""Lab 8, part 1: tracing changes nothing the agent says or does.

The proof is deterministic: the stub model returns fixed replies and fixed token counts, so the same fixture
cases must give identical replies, citations, actions, hand-offs and mock state with trace_steps off and on.
A live run's flips cannot prove this, because the live model varies a little between runs anyway.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import Agent  # noqa: E402
from app.settings import validate  # noqa: E402
from app.types import Message, Principal  # noqa: E402
from mock_api import MockClient  # noqa: E402

PROSPECT = Principal("prospect-01", "prospect", False, None)
ANA = Principal("acct-1001-owner", "customer", True, "acct-1001")
CASES = [
    (PROSPECT, "How much is Pro per seat if we pay every month?"),
    (ANA, "Can you quote us 50 Pro seats on an annual term?"),
    (ANA, "yes"),
    (PROSPECT, "Can I get a 40 percent discount on 20 seats?"),
    (PROSPECT, "What is your gross margin on each plan?"),
]


@pytest.fixture(autouse=True)
def stub_model(monkeypatch):
    monkeypatch.setenv("DW_MODEL_PATH", "stub")


def play(trace_steps: str):
    s = validate({"pack": "quillon", "model_path": "stub", "rules": "on", "tools": "on", "defences": ["access", "output_check"],
                  "trace_steps": trace_steps})
    pd = ROOT / "packs" / "quillon"
    agent = Agent(s, pd, MockClient(pd, "neutral-" + trace_steps))
    out = []
    for i, (who, text) in enumerate(CASES):
        r = agent.handle(Message(f"r{i}", "c1", who, text))
        out.append({"text": r.text, "citations": r.citations, "actions": [a["name"] for a in r.actions], "pending": r.pending,
                    "handoff": r.handoff, "ranked": r.eval.ranked_hit_ids, "delivered": r.eval.delivered_evidence_ids,
                    "tokens": [(u["tokens_in"], u["tokens_out"]) for u in r.usage], "spans": len(r.eval.spans)})
    return out, agent.mock.state()


def test_replies_actions_and_state_are_identical_with_tracing_off_and_on():
    off, state_off = play("off")
    on, state_on = play("on")
    for a, b in zip(off, on):
        assert {k: v for k, v in a.items() if k != "spans"} == {k: v for k, v in b.items() if k != "spans"}
    for key in ("quotes", "bookings", "handoffs", "claims", "counts"):          # what the agent did to the mock, not its ids and times
        assert state_off[key] == state_on[key], key
    assert state_off["counts"]["quotes_created"] == 1


def test_tracing_is_really_on_in_the_second_run():
    off, _ = play("off")
    on, _ = play("on")
    assert all(b["spans"] > a["spans"] for a, b in zip(off, on)), "trace_steps on must add step spans"
