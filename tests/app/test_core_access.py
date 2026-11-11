"""The access check on every path: ranked hits, expansions, links, history, tool results and handoff notes."""
import pytest
from fixtures_app import ANA, BEN, PROSPECT, STAFF, make_agent, msg

from app.core import Agent
from app.security import access
from app.tools import ToolBox
from app.types import Principal

MARGIN = "How is gross margin calculated for each plan?"


def internal_ids(agent):
    return {d for d, doc in agent.index.docs.items() if doc.meta["audience"] == "internal" or doc.meta["owner_scope"] != "everyone"}


def test_allowed_rules():
    pub = {"kind": "chunk", "audience": "public", "owner_scope": "everyone"}
    internal = {"kind": "chunk", "audience": "internal", "owner_scope": "staff"}
    acct = {"kind": "chunk", "audience": "public", "owner_scope": "account:acct-1001"}
    assert access.allowed(pub, PROSPECT) and not access.allowed(internal, PROSPECT) and not access.allowed(internal, ANA)
    forged = Principal("p-x", "staff", False, None)                       # a role claim without verification is nothing
    assert not access.allowed(internal, forged) and access.allowed(internal, STAFF)
    assert access.allowed(acct, ANA) and not access.allowed(acct, BEN) and not access.allowed(acct, STAFF)
    assert access.allowed({"kind": "history", "principal_id": ANA.id}, ANA) and not access.allowed({"kind": "history", "principal_id": ANA.id}, BEN)
    assert not access.allowed({"kind": "mystery"}, STAFF)                  # unknown kinds are refused
    assert not access.allowed({"kind": "tool_result", "account_id": "acct-1004"}, ANA)
    assert access.allowed({"kind": "tool_result", "account_id": "acct-1001"}, ANA)
    assert not access.allowed({"kind": "note", "items": [pub, internal]}, ANA)


@pytest.mark.parametrize("pack,query", [("quillon", MARGIN), ("juniper", "How do I get a fee waiver or booking override?"),
                                        ("saltmarsh", "What is the claims playbook and commission grid?")])
def test_ranked_hits_never_include_internal_chunks_with_access_on(pack, query):
    off = make_agent(pack)
    on = make_agent(pack, defences=["access"], top_k=5)
    assert {c.doc_id for c in off.retrieve(query, PROSPECT).ranked} & internal_ids(off)
    res = on.retrieve(query, PROSPECT)
    assert len(res.ranked) == 5                                            # still a full top 5, drawn from what the principal may see
    assert not {c.doc_id for c in res.ranked} & internal_ids(on)
    assert {c.doc_id for c in on.retrieve(query, STAFF).ranked} & internal_ids(on)    # staff still can


def test_allowed_is_asked_about_every_path(monkeypatch):
    seen = []
    real = access.allowed

    def spy(item, principal):
        seen.append(item["kind"])
        return real(item, principal)
    monkeypatch.setattr(access, "allowed", spy)
    for mode in ("neighbours", "section_parent", "link_hop"):
        agent = make_agent(defences=["access"], context=mode)
        agent.retrieve("pricing faq", PROSPECT)
    assert {"chunk", "neighbour", "section", "link"} <= set(seen)
    agent = make_agent(defences=["access"])
    agent.handle(msg("hello", ANA))
    assert "history" in seen


def test_a_link_to_an_internal_page_is_dropped():
    q = "pricing faq"
    off = make_agent(context="link_hop")
    on = make_agent(context="link_hop", defences=["access"])
    assert "doc-staff-discount-ladder" in {c.doc_id for c in off.retrieve(q, PROSPECT).expanded}
    res = on.retrieve(q, PROSPECT)
    assert "doc-staff-discount-ladder" not in {c.doc_id for c in res.expanded + res.delivered}
    assert not {c.doc_id for c in res.delivered} & internal_ids(on)


def test_neighbours_and_sections_cannot_pull_in_hidden_documents():
    for mode in ("neighbours", "section_parent"):
        agent = make_agent(defences=["access"], context=mode, top_k=8)
        res = agent.retrieve(MARGIN, PROSPECT)
        assert not {c.doc_id for c in res.expanded + res.delivered} & internal_ids(agent)


def test_history_of_another_principal_is_empty():
    agent = make_agent(defences=["access"])
    agent.handle(msg("My secret project is Falcon.", ANA, conv="victim-conv"))
    agent.handle(msg("What did I say before?", BEN, conv="victim-conv"))
    assert not any("Falcon" in m["content"] for m in agent.model.calls[1]["messages"])


def test_a_tool_result_for_someone_elses_account_is_refused():
    agent = make_agent(tools="on", defences=["access"])
    box = ToolBox("quillon", agent.pack_dir, agent.mock)
    call = {"name": "lookup_account", "arguments": {}}
    tc = box.run(call, ANA, {}, "k1", gate=lambda item: False)             # a gate that refuses the result
    assert tc.refused and "access" in tc.reason


def test_a_handoff_note_carries_no_text_from_items_the_principal_may_not_see():
    secret = None
    agent = make_agent(tools="on", rules="on", defences=["access"])
    internal = next(c for c in agent.index.chunks if c.doc_id == "doc-staff-discount-ladder")
    secret = " ".join(internal.text.split()[20:50])
    agent.model.replies = [f"I can't settle this myself.\nHANDOFF: other | Customer asked about discounts. Notes: {secret}"]
    reply = agent.handle(msg("Please pass me to someone about pricing.", ANA))
    assert reply.handoff is not None
    assert secret not in reply.handoff["note"] and "removed" in reply.handoff["note"]
    off = make_agent(tools="on", rules="on")
    off.model.replies = [f"I can't settle this myself.\nHANDOFF: other | Notes: {secret}"]
    assert secret in off.handle(msg("Please pass me to someone about pricing.", ANA)).handoff["note"]    # without access the note carries it


def test_staff_may_see_internal_documents_through_the_whole_pipeline():
    agent = make_agent(defences=["access"])
    reply = agent.handle(msg(MARGIN, STAFF))
    assert set(reply.eval.delivered_doc_ids) & internal_ids(agent)


def test_core_class_still_builds_with_the_stub_gate_off():
    assert isinstance(make_agent(), Agent)


class _OtherHolderMock:
    """A mock that answers lookup_policy with another holder's policy, to test the result check on its own."""
    pack = "saltmarsh"

    def call(self, name, args, principal, key):
        return {"ok": True, "receipt_id": "rcpt-x", "result": {"account_id": "ph-3002", "policy_number": "SM-H-100232"}}


def test_a_signed_in_holder_cannot_certify_another_holders_lookup_policy_result():
    from fixtures_app import ELEANOR, PACKS
    box = ToolBox("saltmarsh", PACKS / "saltmarsh", _OtherHolderMock())
    call = {"name": "lookup_policy", "arguments": {"policy_number": "SM-H-100231", "date_of_birth": "1981-03-14"}}
    state = {}
    tc = box.run(call, ELEANOR, state, "k1", gate=lambda item: access.allowed(item, ELEANOR))
    assert tc.refused and "belongs to someone else" in tc.reason and "verified_account" not in state
    anon = Principal("p-anon", "customer", False, None)                    # not signed in: the lookup itself is the identity proof
    tc = box.run(call, anon, state, "k2", gate=lambda item: access.allowed(item, anon))
    assert not tc.refused and state["verified_account"] == "ph-3002"
