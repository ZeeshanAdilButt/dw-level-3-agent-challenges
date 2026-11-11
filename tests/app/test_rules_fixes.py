"""Rules fixes: Quillon allows only real prices, the clinic keeps its safety hold while symptoms are still described,
Saltmarsh's negation reaches only its own clause, and the router strips PII from its notes."""
import json

from fixtures_app import ELEANOR, PATIENT, make_agent, msg

from app.rules.juniper import JuniperRules
from app.rules.quillon import QuillonRules
from app.rules.saltmarsh import SaltmarshRules

TABLE = "| Pro | PLN-PRO-50 | $38 | $32 | EUR 35 | EUR 30 | 10 seats | 50 seats | 500 GB |"


def quillon():
    return QuillonRules(make_agent().toolbox.fixture, {})


def test_quillon_numbers_that_are_not_prices_do_not_allow_a_price():
    rules = quillon()
    assert rules.after("Pro is $50 per seat.", {"price_table_text": TABLE, "receipts": []}).hit == "price-without-tool"   # 50 is a seat cap
    assert rules.after("Pro is $2026 a year.", {"price_table_text": "Effective 2026-07-01. " + TABLE, "receipts": []}) is not None


def test_quillon_list_prices_and_quote_totals_are_allowed_without_the_table():
    rules = quillon()
    assert rules.after("Pro is $38 per seat per month, or EUR 30 on annual billing.", {"price_table_text": "", "receipts": []}) is None
    receipt = {"result": {"quote_id": "qt-0001", "seats": 20, "net_total_usd": 7680.0, "list_total_usd": 7680.0}}
    assert rules.after("Your quote is $7,680.", {"price_table_text": "", "receipts": [receipt]}) is None
    assert rules.after("Your quote is $20.", {"price_table_text": "", "receipts": [receipt]}) is not None          # 20 is the seat count


def test_the_clinic_keeps_the_safety_hold_while_symptoms_are_still_described():
    rules = JuniperRules({}, {"region": "Port Avery", "emergency_number": "112"})
    state = {"safety_hold": True}
    d = rules.before(msg("I'm ok now, can we book? My chest is still a bit tight.", PATIENT), state, True)
    assert d is not None and d.hit == "safety-hold" and state["safety_hold"]
    assert rules.before(msg("I am safe now, the ambulance is here.", PATIENT), state, True) is None
    assert state["safety_hold"] is False


def test_the_emergency_note_names_the_number_whatever_the_phrase_ends_with():
    rules = JuniperRules({}, {"region": "Port Avery", "emergency_number": "112"})
    assert "told to call 112." in rules._emergency("chest", "red-flag").handoff["note"]
    rules.emergency_phrase = lambda: "call 112 straight away"
    assert "told to call 112 straight away." in rules._emergency("chest", "red-flag").handoff["note"]


def test_saltmarsh_a_negation_in_an_earlier_clause_does_not_excuse_a_payout_promise():
    rules = SaltmarshRules({}, {})
    assert rules.after("There is no excess to pay, so you are fully covered.", {}).hit == "payout-wording"
    assert rules.after("I can't promise that you are covered.", {}) is None


def test_the_router_strips_emails_and_policy_numbers_from_its_notes():
    agent = make_agent("saltmarsh", topology="router_specialists")
    agent.model.replies = [json.dumps([{"area": "claims", "note": "Help eleanor.whitcombe@mail.example with SM-H-100231."}])]
    agent.handle(msg("How do I report a claim?", ELEANOR))
    specialist_system = agent.model.calls[1]["messages"][0]["content"]
    assert "eleanor.whitcombe@mail.example" not in specialist_system and "SM-H-100231" not in specialist_system

