"""Idempotency (decision C3): a cross-principal id, a concurrent duplicate, a lost response."""
import threading

from fixtures_app import ANA, BEN, make_agent, msg

QUOTE = "Can you quote us 50 Pro seats on an annual term?"


def test_cross_principal_request_id_never_returns_another_principals_reply():
    agent = make_agent(tools="on")
    first = agent.handle(msg(QUOTE, ANA, conv="shared", rid="same-id"))
    second = agent.handle(msg(QUOTE, BEN, conv="shared", rid="same-id"))
    assert second is not first and second.trace_id != first.trace_id
    q = agent.mock.state()["quotes"]
    assert sorted(x["account_id"] for x in q) == ["acct-1001", "acct-1004"]      # each principal got their own quote
    assert len(agent.model.calls) == 4                                              # nothing was served from the other principal's store


def test_repeat_of_a_request_returns_the_stored_reply_and_acts_once():          # the lost response, retried
    agent = make_agent(tools="on")
    m = msg(QUOTE, ANA, rid="lost-1")
    first = agent.handle(m)
    calls_after_first = len(agent.model.calls)
    again = agent.handle(m)
    assert again.text == first.text and again.trace_id == first.trace_id
    assert len(agent.model.calls) == calls_after_first                              # no second model call
    assert agent.mock.state()["counts"]["quotes_created"] == 1                      # one action in the final state


def test_same_request_id_with_different_text_is_not_answered_from_the_store():
    agent = make_agent()
    agent.handle(msg("What does the Pro plan cost?", ANA, rid="r-x"))
    other = agent.handle(msg("What is the uptime commitment?", ANA, rid="r-x"))
    assert "already used" in other.text and other.citations == []


def test_concurrent_duplicates_run_once_and_the_second_gets_in_progress():
    gate, entered = threading.Event(), threading.Event()
    agent = make_agent(tools="on")
    agent.model.gate, agent.model.entered = gate, entered
    m = msg(QUOTE, ANA, rid="dup-1")
    results = {}
    t1 = threading.Thread(target=lambda: results.setdefault("first", agent.handle(m)))
    t1.start()
    assert entered.wait(5)                                                           # the first request is inside the model call
    dup = agent.handle(m)
    assert dup.in_progress is True and dup.actions == []
    gate.set()
    t1.join(5)
    first = results["first"]
    assert first.in_progress is False and first.actions
    assert agent.mock.state()["counts"]["quotes_created"] == 1
    assert agent.handle(m).text == first.text                                        # afterwards the stored reply is returned


def test_the_idempotency_key_reaches_the_mock_so_a_replayed_call_changes_nothing():
    agent = make_agent(tools="on")
    first = agent.handle(msg(QUOTE, ANA, rid="k-1"))
    key = first.actions[0]["idempotency_key"]
    receipt = agent.mock.call("create_quote", {"account_id": "acct-1001", "plan": "PLN-PRO-50", "seats": 50, "term": "annual"}, ANA, key)
    assert receipt["replayed"] is True and agent.mock.state()["counts"]["quotes_created"] == 1


def test_a_failed_request_frees_its_key():
    agent = make_agent()

    def boom(messages, tools, step):
        raise RuntimeError("model down")
    agent.model.replies = [boom]
    m = msg("What does the Pro plan cost?", ANA, rid="fail-1")
    try:
        agent.handle(m)
    except RuntimeError:
        pass
    assert agent.handle(m).in_progress is False                                      # a retry runs
