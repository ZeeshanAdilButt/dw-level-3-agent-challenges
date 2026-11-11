"""The confirmation gate: an action runs without a confirm only when the message names it, or answers a clarify that
the same tool asked. Politeness alone ("please", "can you") is not a request for an action."""
import pytest
from fixtures_app import ANA, PROSPECT, make_agent, msg

from app.rules.common import explicit_request

QUOTE_CALL = {"text": "", "tool_calls": [{"name": "create_quote", "arguments": {"plan": "PLN-PRO-50", "seats": 20, "term": "annual"}}]}
DEMO_CALL = {"text": "", "tool_calls": [{"name": "book_demo", "arguments": {"email": "imogen.hale@ashgrovelegal.example",
                                                                         "slot_id": "slot-20261109-0900", "timezone": "Europe/London"}}]}


def quotes(agent):
    return agent.mock.state()["counts"]["quotes_created"]


@pytest.mark.parametrize("tool,text,want", [
    ("create_quote", "Please, what does Pro cost for 20 seats on annual billing?", False),
    ("create_quote", "Can you tell me about the Pro plan?", False),
    ("create_quote", "I need a quote for 24 Team seats billed monthly.", True),
    ("create_quote", "Quote me 22 Team seats annual.", True),
    ("book_demo", "Could you explain what the demo covers, please?", False),
    ("book_demo", "Book me a demo on 12 November at 13:00 UTC.", True),
    ("book_appointment", "Please, what are your opening hours?", False),
    ("book_appointment", "Book me a GP appointment on Monday 9 November at 09:00.", True),
    ("open_claim", "Can you explain what an excess is, please?", False),
    ("open_claim", "Please open a claim on policy SM-H-100234.", True),
])
def test_a_request_names_the_action_not_just_please(tool, text, want):
    assert explicit_request(tool, text) is want


def test_a_polite_question_does_not_let_an_unrequested_action_skip_the_confirm():
    agent = make_agent(tools="on", rules="on", replies=[QUOTE_CALL])
    r = agent.handle(msg("Please, what does Pro cost for 20 seats on annual billing?", ANA, conv="c-polite"))
    assert r.pending and r.pending.startswith("Please confirm") and quotes(agent) == 0


def test_a_named_request_runs_without_a_confirm():
    agent = make_agent(tools="on", rules="on", replies=[QUOTE_CALL])
    r = agent.handle(msg("Create a quote for 20 Pro seats, annual.", ANA, conv="c-named"))
    assert not (r.pending or "").startswith("Please confirm") and quotes(agent) == 1


def test_the_answer_to_a_clarify_counts_only_for_the_tool_that_asked():
    agent = make_agent(tools="on", rules="on")
    r = agent.handle(msg("Can you quote me some seats?", ANA, conv="c-cl"))
    assert "clarify-quote" in r.eval.rule_hits and r.pending
    agent.model.replies = [QUOTE_CALL]
    agent.handle(msg("Pro, 20 seats, annual.", ANA, conv="c-cl"))
    assert quotes(agent) == 1                                                       # the quote tool asked: the answer is the request

    agent.handle(msg("Can you quote me some seats?", ANA, conv="c-other"))
    agent.model.replies = [DEMO_CALL]
    r = agent.handle(msg("Pro, 20 seats, annual.", ANA, conv="c-other"))
    assert r.pending and r.pending.startswith("Please confirm")                     # the quote clarify never covers a demo booking
    assert agent.mock.state()["counts"]["bookings_created"] == 0


def test_a_model_question_is_not_a_clarify_for_any_tool():
    agent = make_agent(tools="on", rules="on", replies=["ASK: Which plan would you like?"])
    agent.handle(msg("Tell me about your plans for my firm.", ANA, conv="c-ask"))
    agent.model.replies = [QUOTE_CALL]
    r = agent.handle(msg("Pro, 20 seats, annual.", ANA, conv="c-ask"))
    assert r.pending and r.pending.startswith("Please confirm") and quotes(agent) == 0


def test_a_side_question_keeps_the_held_action_for_one_more_reply():
    agent = make_agent(tools="on", rules="on", replies=[QUOTE_CALL])
    agent.handle(msg("What would 20 Pro seats on annual billing come to?", ANA, conv="c-side"))
    agent.handle(msg("What does annual billing mean?", ANA, conv="c-side"))       # neither yes nor no
    r = agent.handle(msg("yes", ANA, conv="c-side"))
    assert "confirm:yes" in r.eval.rule_hits and quotes(agent) == 1


def test_a_held_action_lapses_after_two_unrelated_replies():
    agent = make_agent(tools="on", rules="on", replies=[QUOTE_CALL])
    agent.handle(msg("What would 20 Pro seats on annual billing come to?", ANA, conv="c-lapse"))
    agent.handle(msg("What does annual billing mean?", ANA, conv="c-lapse"))
    agent.handle(msg("And what is the seat minimum on Pro?", ANA, conv="c-lapse"))
    r = agent.handle(msg("yes", ANA, conv="c-lapse"))
    assert "confirm:yes" not in r.eval.rule_hits and quotes(agent) == 0


def test_a_prospect_naming_a_demo_books_it_without_a_confirm():
    agent = make_agent(tools="on", rules="on")
    agent.model.replies = [{"text": "", "tool_calls": [{"name": "book_demo", "arguments": {
        "email": "maya.okafor@harlanmoss.example", "slot_id": "slot-20261109-0900", "timezone": "Europe/London"}}]}]
    r = agent.handle(msg("Book me a demo on 9 November at 09:00 UTC, maya.okafor@harlanmoss.example, Europe/London.", PROSPECT,
                         conv="c-demo"))
    assert agent.mock.state()["counts"]["bookings_created"] == 1, r.text
