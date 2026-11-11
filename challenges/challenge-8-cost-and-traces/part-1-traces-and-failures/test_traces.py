"""Lab 8, part 1: spans. Fixed inputs and the stub model only; no network, no Ollama, no reference numbers.

On the starter `Agent.span` records nothing, so these fail with an AssertionError such as: no span for ('rules', None)
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT, ROOT / "challenges" / "challenge-8-cost-and-traces"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from panel_helper import needs_node, render_panel  # noqa: E402

from app.core import Agent  # noqa: E402
from app.model import ChatResult, ModelClient, cost, price_table  # noqa: E402
from app.settings import validate  # noqa: E402
from app.types import Message, Principal  # noqa: E402
from mock_api import MockClient  # noqa: E402

PROSPECT = Principal("prospect-01", "prospect", False, None)
QUESTION = "How much is Pro per seat if we pay every month?"


@pytest.fixture(autouse=True)
def stub_model(monkeypatch):
    monkeypatch.setenv("DW_MODEL_PATH", "stub")


def make_agent(pack="quillon", **settings):
    s = validate({"pack": pack, "model_path": "stub", "rules": "on", "defences": ["output_check"], **settings})
    pd = ROOT / "packs" / pack
    return Agent(s, pd, MockClient(pd, "traces-" + settings.get("trace_steps", "off")))


def ask(agent, text=QUESTION):
    return agent.handle(Message("r1", "c1", PROSPECT, text))


class PricedModel(ModelClient):
    """Answers with fixed token counts and a priced model name, so the dollars of a call can be checked by hand."""

    def chat(self, messages, tools, span_name, tracer):
        with tracer.span("model", step=span_name) as sp:
            tracer.next_call()
            res = ChatResult(text="Pro costs $38 [doc-pricing-table]", tokens_in=1000, tokens_out=500, model="claude-haiku-5-5")
            sp.model, sp.tokens_in, sp.tokens_out = res.model, res.tokens_in, res.tokens_out
        return res


def test_every_model_call_has_a_span():
    reply = ask(make_agent(trace_steps="on"))
    spans = reply.eval.spans
    model_spans = [s for s in spans if s["name"] == "model"]
    assert len(reply.usage) >= 2 and len(model_spans) == len(reply.usage)
    assert {u["span_id"] for u in reply.usage} == {s["span_id"] for s in model_spans}
    assert all(s["model"] and s["tokens_in"] > 0 for s in model_spans)


def test_model_spans_exist_even_with_trace_steps_off():
    reply = ask(make_agent(trace_steps="off"))
    names = {s["name"] for s in reply.eval.spans}
    assert names == {"handle", "model"}, "with trace_steps off only the root and the model calls record spans"


def test_every_span_has_an_id_and_the_root_has_no_parent():
    spans = ask(make_agent(trace_steps="on")).eval.spans
    ids = [s["span_id"] for s in spans]
    assert len(set(ids)) == len(ids) and all(ids)
    roots = [s for s in spans if s["parent_id"] is None]
    assert [r["name"] for r in roots] == ["handle"]
    assert all(s["parent_id"] in ids for s in spans if s["parent_id"] is not None)


def test_every_child_starts_and_ends_inside_its_parent():
    spans = ask(make_agent(trace_steps="on")).eval.spans
    by_id = {s["span_id"]: s for s in spans}
    children = [s for s in spans if s["parent_id"]]
    assert children
    for s in children:
        p = by_id[s["parent_id"]]
        assert p["start_ms"] <= s["start_ms"] and s["end_ms"] <= p["end_ms"], f"{s['name']} sticks out of {p['name']}"


def test_step_spans_record_only_with_trace_steps_on():
    on = {(s["name"], s["attrs"].get("phase")) for s in ask(make_agent(trace_steps="on")).eval.spans}
    for step in [("rules", None), ("retrieve", None), ("expand", None), ("assemble", None), ("rules", "after"), ("rules", "leak_check")]:
        assert step in on, f"no span for {step}"


def test_the_classifier_span_wraps_its_model_call():
    spans = ask(make_agent("juniper", trace_steps="on"), "What are your opening hours on Saturday?").eval.spans
    classifier = next(s for s in spans if s["name"] == "classifier")
    inner = [s for s in spans if s["parent_id"] == classifier["span_id"]]
    assert [s["name"] for s in inner] == ["model"]


def test_wall_clock_latency_is_the_case_end_minus_start():
    reply = ask(make_agent(trace_steps="on"))
    root = reply.eval.spans[0]
    assert reply.latency_ms == pytest.approx(root["end_ms"] - root["start_ms"])


def test_tokens_and_dollars_are_separate_fields():
    reply = ask(make_agent(trace_steps="on"))
    for s in reply.eval.spans:
        assert not any("usd" in k or "cost" in k for k in s), "a span stores tokens; dollars come from the price table"
    assert all({"tokens_in", "tokens_out", "cost_usd", "hosted_equivalent_usd"} <= set(u) for u in reply.usage)


def test_the_dollars_of_a_call_come_from_its_own_models_prices():
    agent = make_agent(trace_steps="on")
    agent.model = PricedModel(agent.settings)
    reply = ask(agent)
    rates = price_table()["models"]["claude-haiku-5-5"]
    expected = (1000 * rates["input"] + 500 * rates["output"]) / 1e6
    assert expected == pytest.approx(0.00035)
    assert all(u["cost_usd"] == pytest.approx(expected) for u in reply.usage)
    assert cost("qwen3:4b-instruct", 1000, 500)[0] == 0.0, "a local model pays nothing"
    assert cost("qwen3:4b-instruct", 1000, 500)[1] == pytest.approx(expected), "but it has a hosted-equivalent price"


@needs_node
def test_the_trace_view_draws_one_case_as_nested_spans():
    spans = [
        {"span_id": "sp-1", "parent_id": None, "name": "handle", "start_ms": 0, "end_ms": 100, "tokens_in": 0, "tokens_out": 0},
        {"span_id": "sp-2", "parent_id": "sp-1", "name": "retrieve", "start_ms": 5, "end_ms": 25, "tokens_in": 0, "tokens_out": 0},
        {"span_id": "sp-3", "parent_id": "sp-1", "name": "model", "start_ms": 30, "end_ms": 90, "model": "claude-haiku-5-5",
         "tokens_in": 1000, "tokens_out": 500},
    ]
    ctx = {"run": {"id": "r-fixed"}, "cases": [{"id": "q-fixed", "steps": [{"eval": {"spans": spans}}]}],
           "prices": price_table()}
    out = render_panel("trace.js", ctx)
    case_table, step_table = out["tables"]
    assert case_table["caption"].startswith("Case q-fixed")
    assert [r[0] for r in case_table["rows"]] == ["handle", "retrieve", "model"]          # parent first, children in time order
    assert [r[2] for r in case_table["rows"]] == ["100 ms", "20 ms", "60 ms"]               # inclusive durations
    assert case_table["rows"][2][4:] == ["claude-haiku-5-5", "1,000", "500", "$0.00035", "$0.00035"]
    assert [r[0] for r in step_table["rows"]] == ["model", "retrieve"]                      # slowest step first
