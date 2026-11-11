"""Lab 6, part 2: the reviewer. Fixed fixtures and the stub model only.

On the starter these fail with `NotImplementedError: YOUR TURN: ...` from the reviewer.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixtures_teams import ANA, PROSPECT, make_agent, msg  # noqa: E402

from app.agents.base import Turn  # noqa: E402
from app.agents.reviewer import review  # noqa: E402
from app.trace import Tracer  # noqa: E402

PRICE_Q = "How much is Pro per seat if we pay every month?"
ROUTER = '[{"area": "sales", "note": "Give the price."}]'


def _turn(agent, text):
    m = msg(text, ANA)
    return Turn(msg=m, tracer=Tracer(m.request_id), state={}, history=[], req_hash="h")


def test_the_reviewer_sees_the_question_the_draft_and_its_citations():
    agent = make_agent(topology="router_specialists_reviewer")
    turn = _turn(agent, PRICE_Q)
    agent.model.replies = [json.dumps({"verdict": "pass"})]
    review(agent, turn, "Pro is $38 per seat per month. [doc-pricing-table]", ["doc-pricing-table"], ["doc-pricing-table", "doc-faq-billing"])
    shown = agent.model.calls[0]["messages"][1]["content"]
    assert PRICE_Q in shown and "Pro is $38 per seat per month." in shown
    assert "CITED: doc-pricing-table" in shown and "doc-faq-billing" in shown


def test_the_reviewer_returns_pass_or_one_revision_request():
    agent = make_agent(topology="router_specialists_reviewer")
    turn = _turn(agent, PRICE_Q)
    agent.model.replies = [json.dumps({"verdict": "revise", "feedback": "Cite the document."})]
    assert review(agent, turn, "Pro is $38.", [], ["doc-pricing-table"]) == {"verdict": "revise", "feedback": "Cite the document."}
    agent.model.replies = ["This looks fine to me."]                               # not JSON: the draft passes, no crash
    assert review(agent, turn, "Pro is $38.", [], []) == {"verdict": "pass"}
    agent.model.replies = [json.dumps({"verdict": "revise", "feedback": "x" * 900})]
    assert len(review(agent, turn, "d", [], [])["feedback"]) <= 300                # a long note is cut


def test_a_passed_draft_costs_one_extra_call_and_a_revision_two():
    agent = make_agent(topology="router_specialists_reviewer")
    reply = agent.handle(msg(PRICE_Q, ANA))
    assert [c["step"] for c in agent.model.calls] == ["router", "specialist:sales", "reviewer"]
    assert [s["name"] for s in reply.eval.spans].count("reviewer") == 1
    agent = make_agent(topology="router_specialists_reviewer")
    agent.model.replies = [ROUTER, "Pro is $38 a month.", json.dumps({"verdict": "revise", "feedback": "Cite the document."}),
                           "Pro is $38 a month. [doc-pricing-table]", json.dumps({"verdict": "revise", "feedback": "again"})]
    reply = agent.handle(msg(PRICE_Q, ANA))
    assert [c["step"] for c in agent.model.calls] == ["router", "specialist:sales", "reviewer", "revise"]   # one revision, never more
    assert reply.citations == ["doc-pricing-table"]


def test_a_revision_counts_as_extra_calls_in_the_usage_record():
    agent = make_agent(topology="router_specialists_reviewer")
    agent.model.replies = [ROUTER, "Pro is $38 a month.", json.dumps({"verdict": "revise", "feedback": "Cite the document."}),
                           "Pro is $38 a month. [doc-pricing-table]"]
    reply = agent.handle(msg(PRICE_Q, ANA))
    assert len(reply.usage) == len(agent.model.calls) == 4
    assert [u["step"] for u in reply.usage][-2:] == ["reviewer", "revise"]


def test_the_revision_is_asked_to_follow_the_feedback():
    agent = make_agent(topology="router_specialists_reviewer")
    agent.model.replies = [ROUTER, "Pro is $38 a month.", json.dumps({"verdict": "revise", "feedback": "Cite the document."}),
                           "Pro is $38 a month. [doc-pricing-table]"]
    agent.handle(msg(PRICE_Q, ANA))
    revise_in = agent.model.calls[3]["messages"][-1]["content"]
    assert "Cite the document." in revise_in and "Pro is $38 a month." in revise_in


def test_the_reply_rules_check_still_runs_last_with_a_reviewer():
    agent = make_agent("saltmarsh", rules="on", topology="router_specialists_reviewer")
    agent.model.replies = ['{"category": "none"}', '[{"area": "cover", "note": "x"}]',    # the classifier is called first on this pack
                           "You are covered and it will definitely be paid. [doc-hw-c41-storm]", json.dumps({"verdict": "pass"})]
    reply = agent.handle(msg("Is storm damage covered?", PROSPECT))
    assert "payout-wording" in reply.eval.rule_hits and "claims handler" in reply.text
