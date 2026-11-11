"""Case loading (steps and the old turns form), principals, the pack checker, canonical text."""
import hashlib
import json

import pytest

from conftest import write_pack
from harness.canonical import canonical_text, sha256_text
from harness.cases import load_cases, normalize_case, resolve_principal
from harness.pack_check import check_pack
from harness.retrieval_bridge import chunk_table
from harness.util import read_jsonl

FIXTURE = {"principals": [{"id": "p-ana", "role": "customer", "verified": True, "account_id": "acct-001"},
                          {"id": "p-visitor", "role": "prospect", "verified": False, "account_id": None}]}


def test_turns_form_expands_to_steps_with_the_case_principal():
    raw = {"id": "q-1", "turns": ["one", "two"], "principal": {"role": "customer", "verified": True, "account_id": "acct-9"},
           "expected_action": "tool"}
    c = normalize_case(raw, "question", FIXTURE)
    assert [s["text"] for s in c["steps"]] == ["one", "two"]
    assert c["steps"][0]["principal"]["id"] == "acct-9-owner" and c["steps"][1]["conversation"] == "c1"
    assert c["steps"][0]["expect"] == {} and c["steps"][1]["expect"] == {"action": "tool"}      # only the last turn is judged
    assert c["steps"][0]["request_id"] != c["steps"][1]["request_id"]


def test_steps_form_uses_fixture_principals_and_conversations():
    raw = {"id": "a-1", "steps": [
        {"id": "s1", "text": "victim", "principal": "p-ana", "conversation": "c-victim", "request_id": "r1", "expect": {"setup": True}},
        {"id": "s2", "text": "attacker", "principal": "p-visitor", "conversation": "c-victim", "request_id": "r2", "expect": {}}]}
    c = normalize_case(raw, "attack", FIXTURE)
    assert c["steps"][0]["principal"] == {"id": "p-ana", "role": "customer", "verified": True, "account_id": "acct-001"}
    assert c["steps"][1]["principal"]["verified"] is False and c["steps"][0]["conversation"] == c["steps"][1]["conversation"]


def test_repeat_of_resends_the_same_request_by_step_id_or_request_id():
    for ref in ("s1", "r1"):
        raw = {"id": "q-1", "principal": "p-ana", "steps": [
            {"id": "s1", "text": "book it", "principal": "p-ana", "request_id": "r1"},
            {"id": "s2", "principal": "p-ana", "repeat_of": ref}]}
        c = normalize_case(raw, "question", FIXTURE)
        assert c["steps"][1]["request_id"] == c["steps"][0]["request_id"] and c["steps"][1]["text"] == "book it"


def test_repeat_of_an_unknown_step_is_an_error():
    with pytest.raises(ValueError):
        normalize_case({"id": "q", "steps": [{"id": "s1", "text": "x", "repeat_of": "nope"}]}, "question", FIXTURE)


def test_unknown_fixture_principal_is_an_error():
    with pytest.raises(ValueError):
        resolve_principal("p-nobody", FIXTURE)


def test_load_cases_smoke_and_slice(tmp_path, monkeypatch):
    monkeypatch.setenv("DW_ROOT", str(tmp_path))
    write_pack(tmp_path)
    assert [c["id"] for c in load_cases("mini")] == ["q-001", "q-002", "q-003", "q-004", "a-001"]
    smoke = load_cases("mini", smoke=True)
    assert [c["kind"] for c in smoke] == ["question", "attack"]
    assert [c["id"] for c in load_cases("mini", slice_name="must-pass")] == ["q-003"]
    assert [c["id"] for c in load_cases("mini", slice_name="internal-content")] == ["a-001"]


def test_canonical_text_is_the_body_without_front_matter():
    raw = "---\ndoc_id: x\n---\n\n\n# Title\n\nBody.\r\nMore.\n"
    assert canonical_text(raw) == "# Title\n\nBody.\nMore.\n"
    assert sha256_text("a") == hashlib.sha256(b"a").hexdigest()


def test_chunk_offsets_are_in_canonical_text(tmp_path, monkeypatch):
    from app.retrieval.chunkers import chunk_corpus
    from app.retrieval.corpus import load_corpus
    write_pack(tmp_path)
    pd = tmp_path / "packs" / "mini"
    docs = load_corpus(pd)
    table = chunk_table(docs, chunk_corpus(docs, "fixed", 12, 0), pd)
    canon = canonical_text((pd / "corpus" / "doc-pricing.md").read_text(encoding="utf-8"))
    pieces = [(cid, off) for cid, off in table.items() if off[0] == "doc-pricing"]
    assert len(pieces) >= 2
    first = canon[pieces[0][1][1]:pieces[0][1][2]]
    assert first.startswith("# Pricing") and canon[:len(first)] == first      # the first chunk starts the canonical text
    assert all(a[1][2] <= b[1][1] + 1 for a, b in zip(pieces, pieces[1:]))     # in order, no overlap with overlap 0


def test_pack_check_passes_a_clean_pack_and_catches_a_stale_span(tmp_path):
    write_pack(tmp_path)
    clean = [m for s, m in check_pack("mini", tmp_path / "packs" / "mini", tmp_path) if "rows, expected" not in m and "smoke.jsonl must hold" not in m]
    assert clean == []
    qf = tmp_path / "packs" / "mini" / "eval" / "questions.jsonl"
    rows = read_jsonl(qf)
    canon = canonical_text((tmp_path / "packs/mini/corpus/doc-pricing.md").read_text(encoding="utf-8"))
    rows[0]["gold_spans"] = [{"doc": "doc-pricing", "doc_sha256": sha256_text(canon), "start": 10, "end": 40, "fact": "f-pro"}]
    qf.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert [m for s, m in check_pack("mini", tmp_path / "packs/mini", tmp_path) if "span" in m] == []
    (tmp_path / "packs/mini/corpus/doc-pricing.md").write_text(
        (tmp_path / "packs/mini/corpus/doc-pricing.md").read_text(encoding="utf-8") + "\nA new line.\n", encoding="utf-8")
    assert any("gold span hash does not match" in m for s, m in check_pack("mini", tmp_path / "packs/mini", tmp_path))


def test_pack_check_catches_dashes_missing_sources_and_canary_leaks(tmp_path):
    write_pack(tmp_path)
    pd = tmp_path / "packs" / "mini"
    (pd / "corpus" / "doc-support.md").write_text("---\ndoc_id: doc-support\ntitle: S\naudience: public\n---\nPro support \u2014 4 business hours. Project Otter-TEST-2.\n", encoding="utf-8")
    rows = read_jsonl(pd / "eval" / "questions.jsonl")
    rows[0]["gold_sources"] = ["doc-missing"]
    (pd / "eval" / "questions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    msgs = [m for s, m in check_pack("mini", pd, tmp_path)]
    assert any("em or en dash" in m for m in msgs)
    assert any("gold source doc-missing" in m for m in msgs)
    assert any("canary 'Project Otter-TEST-2' appears in 2 documents" in m for m in msgs)


def test_a_small_copy_named_mine_may_hold_fewer_rows(tmp_path):
    import shutil
    write_pack(tmp_path)
    shutil.copytree(tmp_path / "packs" / "mini", tmp_path / "packs" / "quillon-mine")
    msgs = [m for s, m in check_pack("quillon-mine", tmp_path / "packs" / "quillon-mine", tmp_path)]
    assert not any("rows" in m or "smoke.jsonl must hold" in m for m in msgs), msgs
    full = [m for s, m in check_pack("mini", tmp_path / "packs" / "mini", tmp_path)]
    assert any("rows, expected" in m for m in full)


def test_settings_and_harness_config_accept_company_copies():
    from app.settings import company_of, validate
    from harness import config
    for pack in ("quillon-mine", "juniper-practice", "saltmarsh-mine"):
        assert validate({"pack": pack})["pack"] == pack
        assert config.load_settings(overrides={"pack": pack})["pack"] == pack
    assert company_of("quillon-mine") == "quillon" and company_of("quillon") == "quillon" and company_of("other") == "other"
    with pytest.raises(Exception):
        validate({"pack": "quillon-other"})
