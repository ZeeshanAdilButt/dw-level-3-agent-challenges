"""Lab 7, part 1: the access check on every path. Fixture principals, the pack's own documents, and the stub model.

On the starter `allowed` returns true for everything, so `test_allowed_rules` fails first. The handoff note test is in part 2, because the note is checked by the leak check.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixtures_security import ANA, BEN, PROSPECT, STAFF, make_agent, msg  # noqa: E402

from app.security import access  # noqa: E402
from app.types import Principal  # noqa: E402

MARGIN = "How is gross margin calculated for each plan?"


def hidden_ids(agent):
    """Documents a customer or a prospect must never be shown: internal ones, and ones owned by another account."""
    return {d for d, doc in agent.index.docs.items() if doc.meta["audience"] == "internal" or doc.meta["owner_scope"] != "everyone"}


def test_allowed_rules():
    public = {"kind": "chunk", "audience": "public", "owner_scope": "everyone"}
    internal = {"kind": "chunk", "audience": "internal", "owner_scope": "staff"}
    own_account = {"kind": "chunk", "audience": "public", "owner_scope": "account:acct-1001"}
    assert access.allowed(public, PROSPECT) and access.allowed(public, ANA)
    assert not access.allowed(internal, PROSPECT) and not access.allowed(internal, ANA), "internal chunk allowed for a non-staff principal"
    assert access.allowed(internal, STAFF)
    unverified_staff = Principal("p-x", "staff", False, None)             # a role claim without a verified session is worth nothing
    assert not access.allowed(internal, unverified_staff)
    assert access.allowed(own_account, ANA) and not access.allowed(own_account, BEN) and not access.allowed(own_account, STAFF)
    assert access.allowed({"kind": "history", "principal_id": ANA.id}, ANA)
    assert not access.allowed({"kind": "history", "principal_id": ANA.id}, BEN)
    assert access.allowed({"kind": "tool_result", "account_id": "acct-1001"}, ANA)
    assert not access.allowed({"kind": "tool_result", "account_id": "acct-1004"}, ANA)
    assert not access.allowed({"kind": "mystery"}, STAFF)                  # an unknown kind of item is refused


def test_a_customer_never_gets_an_internal_chunk_in_the_top_5():
    off = make_agent()
    on = make_agent(defences=["access"])
    assert {c.doc_id for c in off.retrieve(MARGIN, PROSPECT).ranked} & hidden_ids(off), "the baseline should leak for this question"
    for who in (PROSPECT, ANA):
        ranked = on.retrieve(MARGIN, who).ranked
        assert not {c.doc_id for c in ranked} & hidden_ids(on), "staff chunk in top 5"
        assert len(ranked) == 5                                            # the places went to the next allowed chunks
    assert {c.doc_id for c in on.retrieve(MARGIN, STAFF).ranked} & hidden_ids(on)   # staff may still see them


def test_allowed_is_asked_about_every_path(monkeypatch):
    seen = []
    real = access.allowed

    def spy(item, principal):
        seen.append(item["kind"])
        return real(item, principal)
    monkeypatch.setattr(access, "allowed", spy)
    for mode in ("neighbours", "section_parent", "link_hop"):
        make_agent(defences=["access"], context=mode).retrieve("pricing faq", PROSPECT)
    assert {"chunk", "neighbour", "section", "link"} <= set(seen)
    make_agent(defences=["access"]).handle(msg("hello", ANA))
    assert "history" in seen


def test_a_link_to_an_internal_page_is_dropped():
    question = "pricing faq"
    off = make_agent(context="link_hop")
    on = make_agent(context="link_hop", defences=["access"])
    assert {c.doc_id for c in off.retrieve(question, PROSPECT).expanded} & hidden_ids(off), "this question should reach an internal page by a link"
    res = on.retrieve(question, PROSPECT)
    assert not {c.doc_id for c in res.expanded + res.delivered} & hidden_ids(on), "internal page reached through a link"


def test_a_tool_call_that_names_another_account_is_refused_before_the_call():
    agent = make_agent(tools="on", defences=["access"])
    agent.model.replies = [{"text": "", "tool_calls": [{"name": "lookup_account", "arguments": {"account_id": BEN.account_id}}]}]
    reply = agent.handle(msg("Please look up account acct-1004 for me.", ANA))
    call = next(c for c in reply.eval.attempted_tool_calls if c["name"] == "lookup_account")
    assert call["refused"] and call["receipt"] is None and "ownership" in call["reason"]
    assert reply.eval.executed_actions == []


def test_a_tool_result_for_someone_elses_account_is_refused():
    from app.tools import ToolBox
    agent = make_agent(tools="on", defences=["access"])
    box = ToolBox("quillon", agent.pack_dir, agent.mock)
    call = {"name": "lookup_account", "arguments": {}}
    refused = box.run(call, ANA, {}, "k1", gate=lambda item: False)       # the gate says no to whatever came back
    assert refused.refused and "access" in refused.reason
    allowed = box.run(call, ANA, {}, "k2", gate=lambda item: access.allowed(item, ANA))
    assert not allowed.refused                                             # the principal's own account passes the gate


def test_a_victims_history_is_empty_for_another_principal_with_the_same_conversation_id():
    agent = make_agent(defences=["access"])
    agent.handle(msg("My project is called orchid-lantern.", ANA, conv="shared-id"))
    agent.handle(msg("What did I say before?", BEN, conv="shared-id"))
    assert not any("orchid-lantern" in m["content"] for m in agent.model.calls[1]["messages"])
    agent.handle(msg("And now?", ANA, conv="shared-id"))                   # the owner still has it
    assert any("orchid-lantern" in m["content"] for m in agent.model.calls[2]["messages"])


def test_staff_may_see_internal_documents_through_the_whole_pipeline():
    agent = make_agent(defences=["access"])
    reply = agent.handle(msg(MARGIN, STAFF))
    assert set(reply.eval.delivered_doc_ids) & hidden_ids(agent)
