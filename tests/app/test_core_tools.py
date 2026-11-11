"""Tools: validation, ownership bound to the principal, refusals recorded with a reason, and what the mock enforces."""
import pytest
from fixtures_app import ANA, BEN, CAT, ELEANOR, PARENT, PATIENT, PATIENT_7, PROSPECT, RASHID, make_agent, msg

QUOTE = {"name": "create_quote", "arguments": {"plan": "PLN-PRO-50", "seats": 40, "term": "annual", "discount_pct": 0}}


def run(agent, principal, calls, text="Can you give me a quote please?"):
    """Script the model: first reply asks for the calls, the next one is plain text."""
    agent.model.replies = [{"tool_calls": calls if isinstance(calls, list) else [calls]}, "ok"]
    return agent.handle(msg(text, principal))


def attempted(reply):
    return [(a["name"], a["refused"], a["reason"]) for a in reply.eval.attempted_tool_calls]


def test_a_call_naming_another_account_is_refused_and_never_reaches_the_mock():
    agent = make_agent(tools="on")
    r = run(agent, ANA, {"name": "lookup_account", "arguments": {"account_id": "acct-1004"}})
    (name, refused, reason), = attempted(r)
    assert refused and "ownership" in reason
    assert agent.mock.state()["receipts"] == [] and r.actions == []
    r2 = run(agent, ANA, {"name": "create_quote", "arguments": {**QUOTE["arguments"], "account_id": "acct-1004"}})
    assert attempted(r2)[0][1] and agent.mock.state()["counts"]["quotes_created"] == 0
    r3 = run(agent, ANA, {"name": "lookup_account", "arguments": {"email": "tomas.brandt@delmartreasury.example"}})    # Delmar's contact
    assert attempted(r3)[0][1] and "ownership" in attempted(r3)[0][2]


def test_the_principal_comes_from_the_core_never_from_arguments():
    agent = make_agent(tools="on")
    r = run(agent, ANA, {"name": "create_quote", "arguments": {**QUOTE["arguments"], "principal": "acct-1004-owner", "verified": True}})
    assert attempted(r)[0][1] and "unknown argument" in attempted(r)[0][2]
    r = run(agent, ANA, {"name": "lookup_account", "arguments": {}})                       # omitted: filled from the principal
    assert r.actions[0]["arguments"]["account_id"] == "acct-1001" and r.actions[0]["receipt"]["result"]["company"] == "Ashgrove Legal"
    r = run(agent, ANA, {"name": "create_quote", "arguments": QUOTE["arguments"]})
    assert r.actions[0]["arguments"]["account_id"] == "acct-1001"


@pytest.mark.parametrize("call,fragment", [
    ({"name": "delete_everything", "arguments": {}}, "unknown tool"),
    ({"name": "create_quote", "arguments": {"plan": "PLN-PRO-50", "seats": 40}}, "missing argument"),
    ({"name": "create_quote", "arguments": {**QUOTE["arguments"], "seats": "lots"}}, "whole number"),
    ({"name": "create_quote", "arguments": {**QUOTE["arguments"], "plan": "PLN-GOLD-1"}}, "one of"),
    ({"name": "create_quote", "arguments": {**QUOTE["arguments"], "seats": [40]}}, "whole number"),
])
def test_unknown_tool_missing_field_and_wrong_type_are_refused(call, fragment):
    agent = make_agent(tools="on")
    r = run(agent, ANA, call)
    (name, refused, reason), = attempted(r)
    assert refused and fragment in reason
    assert agent.mock.state()["receipts"] == []


def test_an_unverified_principal_is_refused_for_account_tools():
    agent = make_agent(tools="on")
    for call in ({"name": "lookup_account", "arguments": {}}, QUOTE):
        r = run(agent, PROSPECT, call)
        assert attempted(r)[0][1] and "not verified" in attempted(r)[0][2]
    assert agent.mock.state()["receipts"] == []


def test_the_mock_refuses_what_the_core_would_let_through_when_the_rule_is_company_policy():
    agent = make_agent(tools="on")
    over = {"name": "create_quote", "arguments": {**QUOTE["arguments"], "discount_pct": 12}}
    r = run(agent, ANA, over)
    rec = r.eval.attempted_tool_calls[0]["receipt"]
    assert rec["ok"] is False and rec["error"] == "needs_approval"
    assert agent.mock.state()["counts"]["quotes_created"] == 0
    assert r.handoff and r.handoff["reason"] == "discount_over_line"                         # above the line, a person
    assert r.actions == []                                                                    # a refused call is attempted, not executed
    low = run(agent, ANA, {"name": "create_quote", "arguments": {**QUOTE["arguments"], "seats": 500}})
    assert low.eval.attempted_tool_calls[0]["receipt"]["error"] == "seats_out_of_band"
    ok = run(agent, ANA, {"name": "create_quote", "arguments": {**QUOTE["arguments"], "seats": 50, "discount_pct": 10}})
    q = ok.actions[0]["receipt"]["result"]
    assert (q["list_total_usd"], q["net_total_usd"]) == (19200.0, 17280.0)                     # the list price comes from the price book


def test_book_demo_takes_one_slot_and_a_booked_slot_is_gone():
    agent = make_agent(tools="on")
    call = {"name": "book_demo", "arguments": {"email": "maya.okafor@harlanmoss.example", "slot_id": "slot-20261112-1300", "timezone": "Europe/London"}}
    assert run(agent, PROSPECT, call).actions
    again = run(agent, PROSPECT, call)
    assert again.eval.attempted_tool_calls[0]["receipt"]["error"] == "slot_unavailable"
    assert agent.mock.state()["counts"]["bookings_created"] == 1


# ---- the clinic ----------------------------------------------------------------------------------------------------------
def book(slot, service, **extra):
    return {"name": "book_appointment", "arguments": {"slot_id": slot, "service": service, **extra}}


def test_clinic_booking_is_bound_to_the_owner_and_refuses_another_patient():
    agent = make_agent("juniper", tools="on")
    r = run(agent, PATIENT, book("sl-20261110-0930-bf", "blood_fasting", patient_id="pt-2002"))      # Gareth Pell's record
    assert attempted(r)[0][1] and "ownership" in attempted(r)[0][2]
    r = run(agent, PATIENT, book("sl-20261110-0930-bf", "blood_fasting"))                              # patient filled from the principal
    assert r.actions[0]["arguments"]["patient_id"] == "pt-2001" and agent.mock.state()["counts"]["bookings_created"] == 1
    r = run(agent, PARENT, book("sl-20261111-0800-bf", "blood_fasting"))                               # owns two patients: must say which
    assert attempted(r)[0][1] and "patient_id" in attempted(r)[0][2]


def test_the_clinic_mock_enforces_prep_rules():
    agent = make_agent("juniper", tools="on")
    r = run(agent, PATIENT_7, book("sl-20261109-1100-bf", "blood_fasting"))
    rec = r.eval.attempted_tool_calls[0]["receipt"]
    assert not rec["ok"] and rec["message"] == "fasting blood test must start before 10:30"
    r = run(agent, PATIENT, book("sl-20261113-0800-gt", "glucose_tolerance"))                          # Friday
    assert "Monday to Thursday" in r.eval.attempted_tool_calls[0]["receipt"]["message"]
    r = run(agent, PATIENT, book("sl-20261110-0930-ch", "child_check"))                                # an adult
    assert "aged 0 to 5" in r.eval.attempted_tool_calls[0]["receipt"]["message"]
    r = run(agent, PATIENT, book("sl-20261111-1400-mp", "minor_procedure"))                            # no pre-check on file
    assert "pre-check" in r.eval.attempted_tool_calls[0]["receipt"]["message"]
    assert agent.mock.state()["counts"]["bookings_created"] == 0                                       # a refused booking changes nothing


def test_the_clinic_mock_refuses_an_unverified_booking_and_another_owner():
    agent = make_agent("juniper", tools="on")
    box_state = agent.mock
    receipt = box_state.call("book_appointment", {"patient_id": "pt-2001", "slot_id": "sl-20261110-0930-bf", "service": "blood_fasting"}, PROSPECT, "k-1")
    assert receipt["error"] == "not_verified"
    receipt = box_state.call("book_appointment", {"patient_id": "pt-2002", "slot_id": "sl-20261110-0930-bf", "service": "blood_fasting"}, PATIENT, "k-2")
    assert receipt["error"] == "forbidden"


# ---- the insurer -----------------------------------------------------------------------------------------------------------
LOOKUP = {"name": "lookup_policy", "arguments": {"policy_number": "SM-H-100231", "date_of_birth": "1981-03-14"}}


def test_policy_lookup_needs_the_right_date_of_birth_and_verifies_for_the_session():
    agent = make_agent("saltmarsh", tools="on")
    wrong = run(agent, PROSPECT, {"name": "lookup_policy", "arguments": {**LOOKUP["arguments"], "date_of_birth": "1990-01-01"}})
    assert wrong.eval.attempted_tool_calls[0]["receipt"]["error"] == "identity_not_verified" and "name" not in str(wrong.eval.attempted_tool_calls[0]["receipt"])
    early = run(agent, PROSPECT, {"name": "check_claim", "arguments": {"claim_id": "CLM-26-0412"}})
    assert attempted(early)[0][1] and "identity not verified" in attempted(early)[0][2]
    ok = run(agent, PROSPECT, LOOKUP)
    assert ok.actions[0]["receipt"]["result"]["identity_verified"] is True
    assert agent.mock.state()["verified"][PROSPECT.id] == "ph-3001"


def test_claims_are_owner_only_and_opening_one_makes_status_received():
    agent = make_agent("saltmarsh", tools="on")
    other = run(agent, RASHID, {"name": "check_claim", "arguments": {"claim_id": "CLM-26-0412"}})        # Eleanor's claim
    assert attempted(other)[0][1] and "ownership" in attempted(other)[0][2]
    mine = run(agent, ELEANOR, {"name": "check_claim", "arguments": {"claim_id": "CLM-26-0412"}})
    assert mine.actions[0]["receipt"]["result"]["status"] == "assessing"
    foreign = run(agent, ELEANOR, {"name": "open_claim", "arguments": {"policy_number": "SM-H-100232", "date_of_loss": "2026-11-03",
                                                                      "description": "Burst pipe", "claim_type": "escape_of_water"}})
    assert attempted(foreign)[0][1]
    opened = run(agent, ELEANOR, {"name": "open_claim", "arguments": {"policy_number": "SM-H-100231", "date_of_loss": "2026-11-03",
                                                                     "description": "Burst pipe", "claim_type": "escape_of_water"}})
    assert opened.actions[0]["receipt"]["result"]["status"] == "received"
    future = agent.mock.call("open_claim", {"policy_number": "SM-H-100231", "date_of_loss": "2027-01-01", "description": "x", "claim_type": "theft"}, ELEANOR, "k-f")
    assert future["error"] == "future_date"
    assert agent.mock.state()["counts"]["claims_opened"] == 1


def test_at_most_three_tool_rounds():
    agent = make_agent(tools="on")
    loop = {"tool_calls": [{"name": "lookup_account", "arguments": {}}]}
    agent.model.replies = [loop, loop, loop, "stopped"]
    r = agent.handle(msg("What is my renewal date?", ANA))
    assert len(r.eval.attempted_tool_calls) == 3
    assert agent.model.calls[-1]["tools"] is None          # after the third round the model is asked once more, without tools
    assert r.text == "stopped"


def test_a_specialist_cannot_use_a_tool_outside_its_area():
    agent = make_agent(tools="on", topology="router_specialists")
    agent.model.replies = ['[{"area": "contract", "note": "x"}]', {"tool_calls": [{"name": "create_quote", "arguments": QUOTE["arguments"]}]}, "done"]
    r = agent.handle(msg("quote me", ANA))
    assert attempted(r)[0][1] and "not available to this specialist" in attempted(r)[0][2]
