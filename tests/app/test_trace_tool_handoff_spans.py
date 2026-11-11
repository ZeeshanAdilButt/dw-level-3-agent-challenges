"""trace_steps on adds a span per tool call and for the handoff; off leaves the spans and the reply as they were."""
import os
from pathlib import Path

from app.core import Agent
from app.settings import load_settings
from app.types import Message, Principal
from mock_api import MockClient

ROOT = Path(__file__).resolve().parents[2]


def reply_for(trace):
    os.environ["DW_MODEL_PATH"] = "stub"
    pack = ROOT / "packs" / "juniper"
    agent = Agent(load_settings({"pack": "juniper", "tools": "on", "rules": "on", "trace_steps": trace}), pack, MockClient(pack, "t"))
    return agent.handle(Message("q1", "c", Principal("p", "patient", False, None), "My chest is crushing and my left arm is numb."))


def test_tool_and_handoff_spans_only_with_trace_steps_on():
    on, off = reply_for("on"), reply_for("off")
    names_on = {s["name"] for s in on.eval.spans}
    names_off = {s["name"] for s in off.eval.spans}
    assert {"tool", "handoff"} <= names_on and not ({"tool", "handoff"} & names_off)
    assert on.text == off.text and on.handoff == off.handoff     # tracing never changes the answer
