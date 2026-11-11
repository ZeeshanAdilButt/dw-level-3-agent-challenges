"""Lab 4, part 2: which document wins when two disagree. A small pack is written into a temporary folder.
The evaluation date is fixed at 2026-11-01. No model beyond the stub, no real pack, no reference numbers."""
import shutil
from pathlib import Path

import pytest

from app import context
from app.core import Agent
from app.retrieval.index import Index
from app.settings import validate
from app.types import Message, Principal
from mock_api import MockClient

ROOT = Path(__file__).resolve().parents[3]


def doc(doc_id, topic, text, authority="guide", chain=None, scope="everyone", start="2025-01-01", end=None, product=None, supersedes=None):
    front = [f"doc_id: {doc_id}", f"title: {doc_id}", "audience: public", f"owner_scope: {scope}", f"topic: {topic}", f"authority: {authority}",
             f"version_chain: {chain or doc_id}", f'effective_from: "{start}"']
    if end:
        front.append(f'effective_to: "{end}"')
    if product:
        front.append(f"applies_to: {{product: [{product}]}}")
    if supersedes:
        front.append(f"supersedes: {supersedes}")
    return doc_id, "\n".join(front), text


DOCS = [
    # Across kinds: a newer brochure says flood is covered, the older policy wording says it is excluded. The wording wins whatever the dates.
    doc("doc-flood-brochure", "flood", "Our brochure says flood damage is covered.", authority="brochure", scope="marketing", start="2026-06-01"),
    doc("doc-flood-wording", "flood", "The wording says flood damage is excluded.", authority="wording", scope="underwriting", start="2025-01-01"),
    # Inside one chain and scope: the newer effective date wins.
    doc("doc-excess-2025", "excess", "The excess is one hundred.", authority="wording", chain="excess-chain", scope="underwriting", start="2025-01-01"),
    doc("doc-excess-2026", "excess", "The excess is two hundred.", authority="wording", chain="excess-chain", scope="underwriting", start="2026-03-01"),
    # Inside one chain: a document that supersedes the other wins even when its date is older.
    doc("doc-term-old", "term", "The term is twelve months.", authority="rule", chain="term-chain", scope="sales", start="2026-05-01"),
    doc("doc-term-new", "term", "The term is thirty months.", authority="rule", chain="term-chain", scope="sales", start="2026-02-01", supersedes="doc-term-old"),
    # Nothing separates these two: same kind, different chains. A conflict.
    doc("doc-pets-a", "pets", "Pets are covered for injury.", chain="pets-a", scope="sales"),
    doc("doc-pets-b", "pets", "Pets are not covered for injury.", chain="pets-b", scope="claims"),
    # Not part of a conflict: not yet in force, no longer in force, and for another product.
    doc("doc-boat-future", "boats", "Boats are covered from next year.", authority="wording", start="2027-01-01"),
    doc("doc-boat-now", "boats", "Boats are covered at sea only.", authority="guide", chain="boats-now", start="2025-01-01"),
    doc("doc-gap-expired", "garden", "Garden furniture is covered.", authority="wording", start="2024-01-01", end="2026-06-30"),
    doc("doc-gap-now", "garden", "Garden furniture is not covered.", authority="guide", chain="garden-now", start="2025-01-01"),
    doc("doc-bike-motor", "bikes", "Motor policy bike cover is full.", authority="wording", product="motor"),
    doc("doc-bike-home", "bikes", "Home policy bike cover is limited.", authority="guide", chain="bike-home", product="home"),
    # A different topic: never dropped for another topic's document.
    doc("doc-claims-phone", "claims-phone", "Call the claims line to report a loss.", authority="brochure", scope="marketing"),
]


def doc_topics(doc_id, topics, text, authority="guide", groups=None, start="2025-01-01"):
    """A document that states several rules: `topics` maps each topic to (about, claim)."""
    front = [f"doc_id: {doc_id}", f"title: {doc_id}", "audience: public", "owner_scope: everyone", f"authority: {authority}",
             f"version_chain: {doc_id}", f'effective_from: "{start}"', "topics:"]
    for t, (about, claim) in topics.items():
        front += [f"  {t}:", f"    about: {about}", f"    claim: {claim}"]
    if groups:
        front.append(f"applies_to: {{customer_group: [{groups}]}}")
    return doc_id, "\n".join(front), text


DOCS += [
    # Two current documents that make the same claim agree: neither is dropped, and there is no conflict.
    doc_topics("doc-rate-table", {"rate-pro": ("Pro rate", "rate-12"), "rate-team": ("Team rate", "rate-9")}, "Pro is 12, Team is 9.", authority="rule"),
    doc_topics("doc-rate-pro", {"rate-pro": ("Pro rate", "rate-12")}, "The Pro rate is 12.", authority="rule"),
    doc_topics("doc-rate-guide", {"rate-pro": ("Pro rate", "rate-12")}, "Our guide: the Pro rate is 12.", authority="guide"),
    # A FAQ that disagrees on the Team rate only.
    doc_topics("doc-rate-faq", {"rate-team": ("Team rate", "rate-7")}, "The Team rate is 7.", authority="faq"),
    # An endorsement for the policies that carry it, against the wording for everyone.
    doc_topics("doc-lock-wording", {"locks": ("Lock condition", "locks-any")}, "Any lock will do.", authority="wording"),
    doc_topics("doc-lock-endorsement", {"locks": ("Lock condition", "locks-5-lever")}, "A five-lever lock is needed.", authority="endorsement",
               groups="policies that carry this endorsement", start="2026-08-01"),
]


@pytest.fixture
def pack(tmp_path):
    pack = tmp_path / "quillon"                     # a known pack name, so the core accepts it
    (pack / "corpus").mkdir(parents=True)
    (pack / "tools").mkdir()
    shutil.copy(ROOT / "packs" / "quillon" / "tools" / "fixture.json", pack / "tools" / "fixture.json")
    for doc_id, front, text in DOCS:
        (pack / "corpus" / f"{doc_id}.md").write_text(f"---\n{front}\n---\n{text}\n", encoding="utf-8")
    return pack


def index_of(pack):
    return Index(pack, {"chunker": "fixed", "chunk_size": 400, "overlap": 0, "retriever": "bm25"})


def decide(pack, ids, query="anything"):
    return context.apply_authority(index_of(pack), ids, query)


def test_the_evaluation_date_is_fixed():
    assert context.EVAL_DATE == "2026-11-01"


def test_a_document_that_does_not_apply_is_not_part_of_a_conflict(pack):
    dropped, conflict = decide(pack, ["doc-boat-future", "doc-boat-now"])          # the wording is not in force yet
    assert dropped == set() and conflict is None
    dropped, conflict = decide(pack, ["doc-gap-expired", "doc-gap-now"])           # the wording ended on 2026-06-30
    assert dropped == set() and conflict is None
    dropped, conflict = decide(pack, ["doc-bike-motor", "doc-bike-home"], query="what is the home policy bike cover")
    assert dropped == set() and conflict is None                                   # the motor document is about another product


def test_inside_one_chain_the_newer_document_wins(pack):
    dropped, conflict = decide(pack, ["doc-excess-2025", "doc-excess-2026"])
    assert dropped == {"doc-excess-2025"} and conflict is None
    dropped, conflict = decide(pack, ["doc-excess-2026", "doc-excess-2025"])       # the order of the list does not matter
    assert dropped == {"doc-excess-2025"}
    dropped, conflict = decide(pack, ["doc-term-old", "doc-term-new"])             # supersedes beats the date
    assert dropped == {"doc-term-old"} and conflict is None


def test_across_kinds_the_higher_authority_wins_whatever_the_dates(pack):
    dropped, conflict = decide(pack, ["doc-flood-brochure", "doc-flood-wording"])  # the brochure is newer, the wording outranks it
    assert dropped == {"doc-flood-brochure"} and conflict is None


def test_any_other_pair_is_a_conflict(pack):
    dropped, conflict = decide(pack, ["doc-pets-a", "doc-pets-b"])
    assert dropped == set()
    assert conflict["reason"] == "documents disagree" and conflict["topic"] == "pets" and set(conflict["docs"]) == {"doc-pets-a", "doc-pets-b"}


def test_documents_of_different_topics_are_never_dropped_for_each_other(pack):
    dropped, conflict = decide(pack, ["doc-claims-phone", "doc-flood-wording", "doc-excess-2026", "doc-pets-a"])
    assert dropped == set() and conflict is None                                   # one document per topic: no group of two


def test_the_winner_is_delivered_and_the_loser_is_not(pack):
    s = {"chunker": "fixed", "chunk_size": 400, "overlap": 0, "retriever": "bm25", "top_k": 5, "context": "none", "neighbours_n": 1,
         "context_token_limit": 3000, "authority_rule": "on", "embed_model": "nomic-embed-text"}
    index = index_of(pack)
    who = Principal("p", "customer", True, None)
    res = context.retrieve(index, "is flood damage covered", who, s)
    assert {"doc-flood-brochure", "doc-flood-wording"} <= {c.doc_id for c in res.ranked}      # both were found
    assert res.dropped_docs == ["doc-flood-brochure"]
    assert "doc-flood-wording" in res.delivered_doc_ids and "doc-flood-brochure" not in res.delivered_doc_ids
    off = context.retrieve(index, "is flood damage covered", who, dict(s, authority_rule="off"))
    assert "doc-flood-brochure" in off.delivered_doc_ids                           # with the rule off, nothing is dropped


def agent_for(pack):
    s = validate({"pack": "quillon", "model_path": "stub", "authority_rule": "on", "chunk_size": 400, "top_k": 5})
    return Agent(s, pack, MockClient(pack, "test"))


def test_a_conflict_sets_the_handoff_reason(pack):
    agent = agent_for(pack)
    who = Principal("prospect-01", "prospect", False, None)
    reply = agent.handle(Message("r1", "c1", who, "are pets covered for injury"))
    assert reply.handoff and reply.handoff["reason"] == "documents disagree"
    assert "doc-pets-a" in reply.handoff["note"] and "doc-pets-b" in reply.handoff["note"]
    fine = agent.handle(Message("r2", "c2", who, "is flood damage covered"))
    assert fine.handoff is None                                                    # the rule picked a winner, so no person is needed


def test_documents_that_agree_are_all_kept(pack):
    dropped, conflict = decide(pack, ["doc-rate-table", "doc-rate-pro", "doc-rate-guide"], query="what is the pro rate")
    assert dropped == set() and conflict is None                                   # one claim: nothing to settle


def test_a_topic_the_question_is_not_about_takes_no_part(pack):
    ids = ["doc-rate-table", "doc-rate-faq"]
    assert decide(pack, ids, query="what is the pro rate") == (set(), None)        # the Team disagreement is not in question
    dropped, conflict = decide(pack, ids, query="what is the team rate")
    assert dropped == {"doc-rate-faq"} and conflict is None                        # the rule outranks the FAQ


def test_a_document_for_some_customers_against_one_for_everyone_is_a_conflict(pack):
    dropped, conflict = decide(pack, ["doc-lock-wording", "doc-lock-endorsement"], query="what is the lock condition")
    assert dropped == set()
    assert conflict["topic"] == "locks" and set(conflict["docs"]) == {"doc-lock-wording", "doc-lock-endorsement"}
