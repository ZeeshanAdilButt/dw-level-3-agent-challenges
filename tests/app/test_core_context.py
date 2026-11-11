"""Citations, the context budget and dedupe, the three evidence stages, and the authority rule."""
import shutil

import pytest
from fixtures_app import ANA, PACKS, PROSPECT, make_agent, msg

QUERY = "What is the uptime commitment and the service credit for missing it?"


def test_citations_are_kept_only_if_the_document_was_delivered():
    agent = make_agent()
    delivered = agent.retrieve(QUERY, PROSPECT).delivered_doc_ids
    assert delivered
    agent.model.replies = [f"Credits apply [{delivered[0]}]. Also see [doc-never-delivered] and [{delivered[0]}, doc-also-fake]."]
    reply = agent.handle(msg(QUERY))
    assert reply.citations == [delivered[0]]
    assert "doc-never-delivered" in reply.text                  # the marker stays in the text; it just is not a valid citation


def test_a_document_reached_through_a_link_can_be_cited():
    agent = make_agent(context="link_hop")
    q = "pricing faq"
    res = agent.retrieve(q, PROSPECT)
    linked = [c.doc_id for c in res.expanded if c.doc_id not in {r.doc_id for r in res.ranked}]
    assert linked
    agent.model.replies = [f"See [{linked[0]}]."]
    assert agent.handle(msg(q)).citations == [linked[0]]


def test_three_evidence_stages_and_one_global_budget():
    agent = make_agent(context="neighbours", neighbours_n=2, context_token_limit=700)
    res = agent.retrieve(QUERY, PROSPECT)
    ranked, expanded = res.ranked_ids, res.expanded_ids
    assert expanded and not set(ranked) & set(expanded)                       # stage 2 adds only new chunks
    assert res.delivered_ids == [c for c in (ranked + expanded) if c in res.delivered_ids]       # ranked first, then expansions in order
    assert res.delivered_tokens <= 700 and res.truncated is True
    assert res.delivered_tokens == sum(c.tokens for c in res.delivered)
    assert len(res.delivered_ids) == len(set(res.delivered_ids))              # no duplicates
    reply = agent.handle(msg(QUERY))
    assert reply.eval.delivered_tokens <= 700 and reply.eval.truncated
    assert reply.eval.ranked_hit_ids == ranked and reply.eval.expanded_evidence_ids == expanded


def test_no_budget_pressure_means_no_truncation_and_exact_stage_equality():
    agent = make_agent(context="none")
    res = agent.retrieve(QUERY, PROSPECT)
    assert res.expanded == [] and res.delivered_ids == res.ranked_ids and not res.truncated


@pytest.mark.parametrize("mode", ["neighbours", "section_parent", "link_hop"])
def test_expansions_are_deduplicated_against_the_hits(mode):
    agent = make_agent(context=mode, top_k=8)
    res = agent.retrieve(QUERY, PROSPECT)
    assert len(set(res.delivered_ids)) == len(res.delivered_ids)
    texts = [c.text.strip() for c in res.delivered]
    assert len(set(texts)) == len(texts)


def test_neighbours_stop_at_the_edge_of_the_document():
    agent = make_agent(context="neighbours", neighbours_n=5)
    res = agent.retrieve(QUERY, PROSPECT)
    for c in res.expanded:
        assert 0 <= c.position < len(agent.index.by_doc[c.doc_id])


def test_link_hop_follows_one_level_only():
    agent = make_agent(context="link_hop", top_k=3)
    res = agent.retrieve("pricing faq", PROSPECT)
    first = {c.doc_id for c in res.ranked}
    links = {t for d in first for t in agent.index.docs[d].links}
    assert {c.doc_id for c in res.expanded} <= links


# ---- the authority rule --------------------------------------------------------------------------------------------------
def doc(doc_id, body, **meta):
    base = {"title": doc_id, "audience": "public", "owner_scope": "everyone", "authority": "guide", "version_chain": doc_id,
            "effective_from": "2026-01-01", "supersedes": None, "links": [], "type": "policy"}
    base.update(meta, doc_id=doc_id)
    import yaml
    return f"---\n{yaml.safe_dump(base)}---\n\n# {doc_id}\n\n{body}\n"


@pytest.fixture
def mini_pack(tmp_path):
    """A tiny Quillon pack with planted conflicts, so the authority rule is tested on known pairs."""
    pack = tmp_path / "quillon"
    (pack / "corpus").mkdir(parents=True)
    (pack / "tools").mkdir()
    shutil.copy(PACKS / "quillon" / "tools" / "fixture.json", pack / "tools" / "fixture.json")
    files = {
        # same chain and scope: the newer one wins, the older is dropped
        "refund-old": doc("doc-refund-old", "Refund window is 14 days for the zebra plan.", version_chain="refund", effective_from="2025-01-01", topic="refund"),
        "refund-new": doc("doc-refund-new", "Refund window is 30 days for the zebra plan.", version_chain="refund", effective_from="2026-06-01", topic="refund",
                          supersedes="doc-refund-old"),
        # across kinds: a newer brochure loses to older wording
        "term-wording": doc("doc-term-wording", "Minimum term for the zebra contract is 12 months.", authority="wording", version_chain="term-w",
                            effective_from="2025-01-01", topic="term"),
        "term-brochure": doc("doc-term-brochure", "Minimum term for the zebra contract is 6 months.", authority="brochure", version_chain="term-b",
                             effective_from="2026-09-01", topic="term"),
        # same authority, different chains: nothing picks a winner
        "notice-a": doc("doc-notice-a", "Notice period for zebra cancellation is 30 days.", authority="rule", version_chain="notice-a", topic="notice"),
        "notice-b": doc("doc-notice-b", "Notice period for zebra cancellation is 60 days.", authority="rule", version_chain="notice-b", topic="notice"),
        # not in force on 2026-11-01: not part of a conflict
        "fee-now": doc("doc-fee-now", "Setup fee for the zebra plan is 100 dollars.", authority="wording", version_chain="fee", topic="fee", effective_from="2026-01-01"),
        "fee-future": doc("doc-fee-future", "Setup fee for the zebra plan is 200 dollars.", authority="guide", version_chain="fee-f", topic="fee", effective_from="2027-03-01"),
        # different topics are never dropped for each other
        "other-topic": doc("doc-other-topic", "Zebra support hours are nine to five.", authority="brochure", version_chain="hours", topic="hours"),
    }
    for name, text in files.items():
        (pack / "corpus" / f"{name}.md").write_text(text, encoding="utf-8")
    return pack


def authority_agent(pack, **kw):
    return make_agent("quillon", pack_dir=pack, authority_rule="on", top_k=kw.pop("top_k", 2), context_token_limit=3000, **kw)


def delivered(res):
    return set(res.delivered_doc_ids)


def test_newer_wins_inside_a_version_chain(mini_pack):
    res = authority_agent(mini_pack).retrieve("refund window days", PROSPECT)
    assert "doc-refund-new" in delivered(res) and "doc-refund-old" not in delivered(res)
    assert res.dropped_docs == ["doc-refund-old"] and res.conflict is None


def test_without_the_rule_both_are_delivered(mini_pack):
    agent = make_agent("quillon", pack_dir=mini_pack, top_k=2)
    assert {"doc-refund-new", "doc-refund-old"} <= delivered(agent.retrieve("refund window days", PROSPECT))


def test_higher_authority_wins_across_kinds_whatever_the_dates(mini_pack):
    res = authority_agent(mini_pack).retrieve("minimum term months", PROSPECT)
    assert "doc-term-wording" in delivered(res) and "doc-term-brochure" not in delivered(res)


def test_no_rule_picks_a_winner_so_the_core_hands_off(mini_pack):
    agent = authority_agent(mini_pack)
    res = agent.retrieve("cancellation notice period days", PROSPECT)
    assert res.conflict and set(res.conflict["docs"]) == {"doc-notice-a", "doc-notice-b"} and res.conflict["reason"] == "documents disagree"
    reply = agent.handle(msg("cancellation notice period days"))
    assert reply.handoff and reply.handoff["reason"] == "documents disagree" and "doc-notice-a" in reply.handoff["note"]
    assert reply.citations == [] and len(agent.model.calls) == 0            # no model call: the question goes to a person


def test_a_document_not_in_force_is_not_part_of_a_conflict(mini_pack):
    res = authority_agent(mini_pack).retrieve("setup fee dollars", PROSPECT)
    assert res.conflict is None and "doc-fee-now" in delivered(res)
    assert "doc-fee-future" in delivered(res)                               # it stays in context; it just is not in the conflict


def test_documents_of_different_topics_are_never_dropped_for_each_other(mini_pack):
    res = authority_agent(mini_pack, top_k=1).retrieve("support hours nine to five", PROSPECT)
    assert "doc-other-topic" in delivered(res)


def test_saltmarsh_conflict_rule_is_on_whatever_authority_rule_says():
    agent = make_agent("saltmarsh", rules="on", authority_rule="off")
    assert agent.authority_on is True
    assert make_agent("saltmarsh", rules="off", authority_rule="off").authority_on is False
    assert make_agent("quillon", rules="on", authority_rule="off").authority_on is False


def test_the_old_price_table_loses_to_the_new_one_in_the_real_pack():
    agent = make_agent(authority_rule="on")
    res = agent.retrieve("What does the Pro plan cost per seat per month?", PROSPECT)
    assert "doc-pricing-table-2025" not in delivered(res)


def test_a_section_parent_replaces_the_continuation_pieces_of_a_heading_chunker(tmp_path):
    """A heading chunker puts the heading line in front of each later piece of a long section. The section parent still
    holds those pieces, so it takes their place instead of being delivered next to them."""
    pack = tmp_path / "quillon"
    (pack / "corpus").mkdir(parents=True)
    (pack / "tools").mkdir()
    shutil.copy(PACKS / "quillon" / "tools" / "fixture.json", pack / "tools" / "fixture.json")
    rules = " ".join(f"Rule {n} says the walrus fee is {n} dollars." for n in range(1, 13))
    (pack / "corpus" / "long.md").write_text(doc("doc-long", f"## Walrus fees\n\n{rules}"), encoding="utf-8")
    agent = make_agent("quillon", pack_dir=pack, chunker="heading", chunk_size=30, context="section_parent", top_k=10)
    res = agent.retrieve("walrus fee dollars", PROSPECT)
    pieces = [c for c in res.ranked if c.heading == "Walrus fees" and c.text.startswith("Walrus fees\n")]
    assert pieces                                                              # continuation pieces were hits
    assert any(c.chunk_id.startswith("doc-long#sec") for c in res.delivered)
    assert not {c.chunk_id for c in pieces} & set(res.delivered_ids)           # the section took their place
    assert res.delivered_text.count("Rule 12 says") == 1
