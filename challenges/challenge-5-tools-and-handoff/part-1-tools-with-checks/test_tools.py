"""Lab 5, part 1: tools with checks. Fixed fixtures and the stub model only: no network, no reference numbers.

The model is scripted: its first reply asks for the tool calls the test names, and the next one is plain text.
Principals and accounts come from the pack's own fixture (packs/quillon and packs/juniper)."""
import itertools
import threading
from pathlib import Path

import pytest

from app.core import Agent
from app.model import ChatResult, ModelClient
from app.settings import validate
from app.types import Message, Principal
from harness.graders.tool import grade_tool
from mock_api import MockClient

ROOT = Path(__file__).resolve().parents[3]
PACKS = ROOT / "packs"

PROSPECT = Principal("prospect-01", "prospect", False, None)
ANA = Principal("acct-1001-owner", "customer", True, "acct-1001")        # Quillon: Ashgrove Legal
BEN = Principal("acct-1004-owner", "customer", True, "acct-1004")        # Quillon: Delmar Treasury
PATIENT = Principal("acct-5001-owner", "customer", True, "acct-5001")    # Juniper Lane: owns pt-2001
PARENT = Principal("acct-5002-owner", "customer", True, "acct-5002")     # Juniper Lane: owns pt-2002 and pt-2003

_ids = itertools.count(1)
SLOT = "sl-20261110-0930-bf"                                              # a fasting blood test slot that is open
BOOK = {"name": "book_appointment", "arguments": {"slot_id": SLOT, "service": "blood_fasting"}}
QUOTE = {"name": "create_quote", "arguments": {"plan": "PLN-PRO-50", "seats": 40, "term": "annual", "discount_pct": 0}}


class Scripted(ModelClient):
    """Answers from a list of scripted replies, then falls back to the deterministic stub. Can wait on an event."""

    def __init__(self, settings, replies=(), gate=None, entered=None):
        super().__init__(settings)
        self.replies, self.calls, self.gate, self.entered = list(replies), [], gate, entered
        self._lock = threading.Lock()

    def chat(self, messages, tools, span_name, tracer):
        with tracer.span("model", step=span_name) as sp:
            tracer.next_call()
            with self._lock:
                self.calls.append(span_name)
                scripted = self.replies.pop(0) if self.replies else None
            if self.entered:
                self.entered.set()
            if self.gate:
                self.gate.wait(5)
            if scripted is None:
                res = self._stub(messages, tools, span_name)
            else:
                d = scripted if isinstance(scripted, dict) else {"text": scripted}
                calls = [{"id": f"s-{i}", "name": c["name"], "arguments": c.get("arguments", {})} for i, c in enumerate(d.get("tool_calls", []))]
                res = ChatResult(text=d.get("text", ""), tool_calls=calls, tokens_in=10, tokens_out=5, model="stub")
            sp.model, sp.tokens_in, sp.tokens_out = res.model, res.tokens_in, res.tokens_out
        return res


def make_agent(pack="juniper", **settings):
    s = validate({"pack": pack, "model_path": "stub", "tools": "on", **settings})
    return Agent(s, PACKS / pack, MockClient(PACKS / pack, "test"), Scripted(s))


def msg(text, principal, conv="c1", rid=None):
    return Message(rid or f"r{next(_ids)}", conv, principal, text)


def ask(agent, principal, calls, text="Please do that for me."):
    """One turn in which the model asks for `calls`."""
    agent.model.replies = [{"tool_calls": calls if isinstance(calls, list) else [calls]}, "Done."]
    return agent.handle(msg(text, principal))


def tried(reply):
    return [(a["name"], a["refused"], a["reason"]) for a in reply.eval.attempted_tool_calls]


# ---- validation and binding ---------------------------------------------------------------------------------------------
def test_a_call_naming_another_account_is_refused_and_never_reaches_the_mock():
    quillon = make_agent("quillon")
    r = ask(quillon, ANA, {"name": "lookup_account", "arguments": {"account_id": "acct-1004"}})
    (name, refused, reason), = tried(r)
    assert refused and "ownership" in reason
    assert quillon.mock.state()["receipts"] == []
    r = ask(quillon, ANA, {"name": "create_quote", "arguments": {**QUOTE["arguments"], "account_id": "acct-1004"}})
    assert tried(r)[0][1] and quillon.mock.state()["counts"]["quotes_created"] == 0

    clinic = make_agent("juniper")                                           # another patient's record, same rule
    r = ask(clinic, PATIENT, {"name": "book_appointment", "arguments": {**BOOK["arguments"], "patient_id": "pt-2002"}})
    assert tried(r)[0][1] and "ownership" in tried(r)[0][2]
    assert clinic.mock.state()["counts"]["bookings_created"] == 0


def test_the_principal_comes_from_the_core_never_from_the_arguments():
    quillon = make_agent("quillon")
    r = ask(quillon, ANA, {"name": "create_quote", "arguments": {**QUOTE["arguments"], "principal": "acct-1004-owner", "verified": True}})
    assert tried(r)[0][1] and "unknown argument" in tried(r)[0][2]
    r = ask(quillon, ANA, QUOTE)                                             # no account named: the core fills it from the principal
    assert r.actions[0]["arguments"]["account_id"] == "acct-1001"
    clinic = make_agent("juniper")
    r = ask(clinic, PATIENT, BOOK)                                           # no patient named: the core fills the one the principal owns
    assert r.actions[0]["arguments"]["patient_id"] == "pt-2001"


@pytest.mark.parametrize("call,fragment", [
    ({"name": "delete_everything", "arguments": {}}, "unknown tool"),
    ({"name": "create_quote", "arguments": {"plan": "PLN-PRO-50", "seats": 40}}, "missing argument"),
    ({"name": "create_quote", "arguments": {**QUOTE["arguments"], "seats": "lots"}}, "whole number"),
    ({"name": "create_quote", "arguments": {**QUOTE["arguments"], "plan": "PLN-GOLD-1"}}, "one of"),
])
def test_unknown_tool_missing_field_and_wrong_type_are_refused(call, fragment):
    agent = make_agent("quillon")
    r = ask(agent, ANA, call)
    (name, refused, reason), = tried(r)
    assert refused and fragment in reason
    assert agent.mock.state()["receipts"] == []


def test_an_unverified_principal_is_refused_for_account_tools():
    quillon = make_agent("quillon")
    for call in ({"name": "lookup_account", "arguments": {}}, QUOTE):
        r = ask(quillon, PROSPECT, call)
        assert tried(r)[0][1] and "not verified" in tried(r)[0][2]
    assert quillon.mock.state()["receipts"] == []
    clinic = make_agent("juniper")
    r = ask(clinic, PROSPECT, BOOK)
    assert tried(r)[0][1] and "not verified" in tried(r)[0][2]
    assert clinic.mock.state()["counts"]["bookings_created"] == 0


# ---- safe repeats -------------------------------------------------------------------------------------------------------
def test_a_repeated_request_leaves_one_action_in_the_final_state():
    # The planted repeat case: step 2 has repeat_of step 1, so it sends the same request id and the same text.
    agent = make_agent("juniper")
    agent.model.replies = [{"tool_calls": [BOOK]}, "Booked."]
    first = agent.handle(msg("Please book the fasting blood test.", PATIENT, conv="c-repeat", rid="req-1"))
    again = agent.handle(msg("Please book the fasting blood test.", PATIENT, conv="c-repeat", rid="req-1"))
    assert first.actions and again.text == first.text and again.trace_id == first.trace_id
    assert agent.mock.state()["counts"]["bookings_created"] == 1


def test_a_request_id_sent_by_another_principal_is_not_answered_from_the_first_principals_reply():
    agent = make_agent("quillon")
    text = "Can you quote us 50 Pro seats on an annual term?"
    first = agent.handle(msg(text, ANA, conv="shared", rid="same-id"))
    second = agent.handle(msg(text, BEN, conv="shared", rid="same-id"))
    assert second is not first and second.trace_id != first.trace_id
    owners = sorted(q["account_id"] for q in agent.mock.state()["quotes"])
    assert owners == ["acct-1001", "acct-1004"]                              # each principal got a quote of their own


def test_two_concurrent_duplicates_run_one_action_and_the_second_gets_in_progress():
    gate, entered = threading.Event(), threading.Event()
    agent = make_agent("juniper")
    agent.model.replies, agent.model.gate, agent.model.entered = [{"tool_calls": [BOOK]}, "Booked."], gate, entered
    m = msg("Please book the fasting blood test.", PATIENT, rid="dup-1")
    results = {}
    worker = threading.Thread(target=lambda: results.setdefault("first", agent.handle(m)))
    worker.start()
    assert entered.wait(5)                                                    # the first request is inside the model call
    duplicate = agent.handle(m)
    assert duplicate.in_progress is True and duplicate.actions == []
    gate.set()
    worker.join(5)
    assert results["first"].actions and results["first"].in_progress is False
    assert agent.mock.state()["counts"]["bookings_created"] == 1


def test_a_lost_response_retried_with_the_same_request_id_returns_the_stored_reply():
    agent = make_agent("juniper")
    agent.model.replies = [{"tool_calls": [BOOK]}, "Booked."]
    m = msg("Please book the fasting blood test.", PATIENT, rid="lost-1")
    first = agent.handle(m)                                                  # the reply is lost on the way back
    calls_before = len(agent.model.calls)
    retry = agent.handle(m)
    assert retry.text == first.text and len(agent.model.calls) == calls_before   # no second model call
    assert agent.mock.state()["counts"]["bookings_created"] == 1
    key = first.actions[0]["idempotency_key"]                                # and the mock itself ignores a replayed key
    receipt = agent.mock.call("book_appointment", first.actions[0]["arguments"], PATIENT, key)
    assert receipt["replayed"] is True and agent.mock.state()["counts"]["bookings_created"] == 1


# ---- the final-state grader ---------------------------------------------------------------------------------------------
SPEC = {"expected_tool": {"name": "book_appointment", "args": {"slot_id": SLOT, "service": "blood_fasting"},
                          "final_state": {"bookings_created": 1}}}


def step(text, executed=(), attempted=()):
    return {"step_id": "s1", "reply": {"text": text, "actions": list(executed)},
            "eval": {"raw_reply": text, "executed_actions": list(executed), "attempted_tool_calls": list(attempted)}}


def test_the_final_state_grader_fails_a_reply_that_says_booked_while_the_mock_holds_nothing():
    nothing = {"bookings": []}
    liar = grade_tool(SPEC, [step("Your fasting blood test is booked.")], nothing, nothing)
    assert not liar["ok"] and any("was not called" in why for why in liar["reasons"])
    refused = {"name": "book_appointment", "arguments": BOOK["arguments"], "refused": True, "reason": "ownership"}
    stopped = grade_tool(SPEC, [step("Your fasting blood test is booked.", attempted=[refused])], nothing, nothing)
    assert not stopped["ok"] and any("was refused" in why for why in stopped["reasons"])
    ran = {"name": "book_appointment", "arguments": BOOK["arguments"], "refused": False, "receipt": {"ok": True, "result": {}}}
    after = {"bookings": [{"booking_id": "b-1", "slot_id": SLOT}]}
    honest = grade_tool(SPEC, [step("Booked.", executed=[ran], attempted=[ran])], nothing, after)
    assert honest["ok"], honest
    wrong_state = grade_tool(SPEC, [step("Booked.", executed=[ran], attempted=[ran])], nothing, nothing)   # a call ran, the mock still holds nothing
    assert not wrong_state["ok"]
