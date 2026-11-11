"""The contract shape, the baseline agent, history, and the spans and cost of one reply."""
from fixtures_app import ANA, PROSPECT, STAFF, make_agent, msg

from app.types import EvalBlock, Reply

REPLY_KEYS = {"text", "citations", "actions", "pending", "handoff", "usage", "cost_usd", "latency_ms", "trace_id", "in_progress"}


def test_contract_shape():
    agent = make_agent()
    reply = agent.handle(msg("How much is Pro per seat if we pay every month?"))
    assert isinstance(reply, Reply)
    assert set(reply.to_dict()) == REPLY_KEYS
    assert set(reply.to_dict(with_eval=True)) == REPLY_KEYS | {"eval"}
    assert isinstance(reply.text, str) and reply.text
    assert reply.citations and all(c.startswith("doc-") for c in reply.citations)
    assert reply.actions == [] and reply.pending is None and reply.handoff is None
    assert reply.trace_id.startswith("tr-") and reply.latency_ms >= 0
    assert reply.in_progress is False
    ev = reply.eval
    assert isinstance(ev, EvalBlock)
    assert ev.raw_reply == reply.text
    assert 0 < len(ev.ranked_hit_ids) <= 5
    assert set(ev.delivered_evidence_ids) == set(ev.ranked_hit_ids)           # context=none: delivered is the ranked hits
    assert ev.delivered_tokens > 0 and ev.truncated is False
    assert ev.usage and {"model", "tokens_in", "tokens_out"} <= set(ev.usage[0])
    assert ev.spans and ev.attempted_tool_calls == [] and ev.executed_actions == [] and ev.rule_hits == []


def test_baseline_is_plain_rag():
    """Every setting at its default: BM25, fixed 400-word chunks, no tools, no rules, no defences."""
    agent = make_agent()
    s = agent.settings
    assert (s["retriever"], s["chunker"], s["chunk_size"], s["overlap"], s["context"]) == ("bm25", "fixed", 400, 0, "none")
    assert (s["tools"], s["rules"], s["defences"], s["authority_rule"], s["topology"]) == ("off", "off", [], "off", "single")
    reply = agent.handle(msg("Can you quote us 50 Pro seats on an annual term?", ANA))
    assert reply.actions == [] and agent.mock.state()["counts"]["quotes_created"] == 0     # no tools
    assert not any(c["tools"] for c in agent.model.calls)


def test_baseline_leaks_internal_documents_by_design():
    agent = make_agent()
    res = agent.retrieve("How is gross margin calculated for each plan?", PROSPECT)
    docs = {c.doc_id for c in res.ranked}
    internal = {d for d, doc in agent.index.docs.items() if doc.meta["audience"] == "internal"}
    assert docs & internal, "the baseline has no access check, so an internal document ranks for a prospect"


def test_history_is_kept_by_principal_and_conversation():
    agent = make_agent()
    agent.handle(msg("What does the Pro plan cost?", ANA, conv="c-a"))
    agent.handle(msg("And the Team plan?", ANA, conv="c-a"))
    second = agent.model.calls[1]["messages"]
    assert any(m["role"] == "user" and "Pro plan cost" in m["content"] for m in second)       # same principal and conversation: kept
    agent.handle(msg("Hello again", ANA, conv="c-b"))
    assert not any("Pro plan cost" in m["content"] for m in agent.model.calls[2]["messages"])  # another conversation: empty
    agent.handle(msg("Hello", STAFF, conv="c-a"))
    assert not any("Pro plan cost" in m["content"] for m in agent.model.calls[3]["messages"])  # another principal: empty


def test_spans_nested_and_every_model_call_has_one():
    agent = make_agent(tools="on", rules="on", trace_steps="on", context="neighbours")
    reply = agent.handle(msg("Can you quote us 50 Pro seats on an annual term?", ANA))
    spans = {s["span_id"]: s for s in reply.eval.spans}
    roots = [s for s in spans.values() if s["parent_id"] is None]
    assert len(roots) == 1 and roots[0]["name"] == "handle"
    for s in spans.values():
        assert s["end_ms"] >= s["start_ms"]
        if s["parent_id"]:
            p = spans[s["parent_id"]]
            assert p["start_ms"] <= s["start_ms"] and s["end_ms"] <= p["end_ms"]       # inside the parent; durations are never summed
    models = [s for s in spans.values() if s["name"] == "model"]
    assert len(models) == len(reply.usage) >= 2                                         # the call that asked for the tool, and the continuation
    assert {u["span_id"] for u in reply.usage} == {s["span_id"] for s in models}
    assert {"retrieve", "expand", "assemble", "rules"} <= {s["name"] for s in spans.values()}
    assert roots[0]["end_ms"] - roots[0]["start_ms"] == reply.latency_ms


def test_step_spans_are_off_unless_trace_steps_is_on():
    reply = make_agent().handle(msg("What does the Pro plan cost?"))
    assert {s["name"] for s in reply.eval.spans} == {"handle", "model"}


def test_tracing_is_neutral_with_a_stub_model():
    cases = ["Can you quote us 50 Pro seats on an annual term?", "What is the uptime commitment?"]
    out = {}
    for flag in ("off", "on"):
        agent = make_agent(tools="on", rules="on", trace_steps=flag)
        out[flag] = [(r.text, r.citations, r.actions and [a["name"] for a in r.actions]) for r in (agent.handle(msg(t, ANA, rid=f"x{i}")) for i, t in enumerate(cases))]
    assert out["off"] == out["on"]


def test_cost_comes_from_prices_toml():
    reply = make_agent().handle(msg("What does the Pro plan cost?"))
    u = reply.usage[0]
    assert reply.cost_usd == 0.0 and u["cost_usd"] == 0.0                # a local model costs nothing
    assert u["hosted_equivalent_usd"] > 0                                 # the hosted-equivalent column
    assert u["tokens_in"] > 0 and u["tokens_out"] > 0                     # tokens and dollars are separate fields
