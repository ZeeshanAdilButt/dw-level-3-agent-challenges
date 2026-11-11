"""Lab 2, part 1: five cuts, one candidate. Fixed documents and fixed delivered texts: no model, no reference numbers.

Invariant (passes on the starter): test_settings_validator, test_the_results_checker_on_fixed_records.
Acceptance (fails on the starter): test_chunkers and test_context_fact_recall (NotImplementedError: YOUR TURN: ...),
and test_results_table (AssertionError: results.md has no screen table).
"""
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "challenges" / "_shared"))

from panel_render import is_reference_tree  # noqa: E402

from app.retrieval.chunkers import by_heading, fixed  # noqa: E402


def doc(body, title="Plans", doc_id="doc-x"):
    return SimpleNamespace(doc_id=doc_id, title=title, body=body)


WORDS = " ".join(f"w{i}" for i in range(10))          # ten tokens: w0 ... w9


def texts(chunks):
    return [c.text.split() for c in chunks]


def w(a, b):
    return [f"w{i}" for i in range(a, b)]


# ---- acceptance: the two chunkers ----------------------------------------------------------------------------------

def test_chunkers():
    # fixed, overlap 0: the chunks tile the document
    assert texts(fixed(doc(WORDS), 4, 0)) == [w(0, 4), w(4, 8), w(8, 10)]
    # overlap 2: start positions step by size - overlap, neighbours share exactly 2 tokens, the last chunk reaches the end
    got = texts(fixed(doc(WORDS), 4, 2))
    assert got == [w(0, 4), w(2, 6), w(4, 8), w(6, 10)]
    assert all(a[-2:] == b[:2] for a, b in zip(got, got[1:]))
    # overlap one below the size: step 1
    got = texts(fixed(doc(WORDS), 4, 3))
    assert len(got) == 7 and got[-1] == w(6, 10)
    # an empty document gives no chunks; a short one gives one
    assert fixed(doc(""), 4, 0) == []
    assert texts(fixed(doc("w0 w1"), 4, 0)) == [["w0", "w1"]]
    # ids, positions and the heading each chunk keeps
    chunks = fixed(doc(WORDS, title="Plans", doc_id="doc-pricing"), 4, 0)
    assert [c.chunk_id for c in chunks] == ["doc-pricing#0", "doc-pricing#1", "doc-pricing#2"]
    assert [c.position for c in chunks] == [0, 1, 2] and chunks[0].heading == "Plans"

    # by heading: never crosses a heading, every chunk keeps its heading
    body = "# Pricing\n\nalpha beta gamma\n\n## Limits\n\ndelta epsilon\n\n## Support\n\nzeta"
    chunks = by_heading(doc(body), 400)
    assert [c.heading for c in chunks] == ["Pricing", "Limits", "Support"]
    assert "delta" not in chunks[0].text and "alpha" not in chunks[1].text and "zeta" not in chunks[1].text
    # a section longer than the limit is cut by size, and every piece keeps the heading
    long_body = "## Limits\n\n" + " ".join(f"t{i}" for i in range(30))
    pieces = by_heading(doc(long_body), 10)
    assert len(pieces) >= 3 and all(p.heading == "Limits" for p in pieces)
    assert all("Limits" in p.text for p in pieces)
    assert all(p.tokens <= 10 for p in pieces), "the heading counts toward max_size: no piece may be longer than 10 tokens"
    assert "t0" in pieces[0].text and "t29" in pieces[-1].text
    # no heading at all: one chunk titled with the document title
    plain = by_heading(doc("just one paragraph of text", title="Notes"), 400)
    assert len(plain) == 1 and plain[0].heading == "Notes"


# ---- acceptance: context fact recall -------------------------------------------------------------------------------

FACTS = [
    {"id": "f-pro", "entity": "Pro plan", "forms": ["$38"], "qualifiers": ["per month", "monthly"], "rival_forms": [["$45"]]},
    {"id": "f-team", "entity": "Team plan", "forms": ["$23"], "qualifiers": ["per month", "monthly"]},
    {"id": "f-sla", "entity": "Pro support", "forms": ["4 business hours"]},
]


def test_context_fact_recall():
    from harness.graders.fact import context_fact_recall      # imported here: on the starter this module raises when imported
    found, total, per = context_fact_recall("The Pro plan costs $38 per seat per month. Pro support replies within 4 business hours.", FACTS)
    assert (found, total) == (2, 3) and per == {"f-pro": True, "f-team": False, "f-sla": True}
    # a key fact cut off by the budget counts as missing
    found, total, per = context_fact_recall("The Pro plan costs $38 per seat per month. The Team plan costs", FACTS)
    assert (found, total) == (1, 3) and per["f-team"] is False
    # the qualifier must sit in the same sentence as the value: a table row split from its header loses it
    found, _, per = context_fact_recall("The Pro plan costs $38 per seat. Billing is monthly.", FACTS)
    assert per["f-pro"] is False
    # evidence may hold an old value too: the rival test belongs to the reply, not to the delivered text
    found, _, per = context_fact_recall("The Pro plan costs $38 per seat per month. The Pro plan used to cost $45 per seat per month.", FACTS)
    assert per["f-pro"] is True
    # nothing delivered: nothing found, and the total is still the number of key facts
    assert context_fact_recall("", FACTS)[:2] == (0, 3)


# ---- invariant -----------------------------------------------------------------------------------------------------

def test_settings_validator():
    from app.settings import SettingsError, validate
    assert validate({"chunk_size": 400, "overlap": 399})["overlap"] == 399
    for bad in (400, 401):
        with pytest.raises(SettingsError):
            validate({"chunk_size": 400, "overlap": bad})
    with pytest.raises(SettingsError):
        validate({"chunk_size": 400, "overlap": -1})


# ---- acceptance: results.md agrees with your own screen records ----------------------------------------------------

EXPECTED = {("fixed", 200, 0), ("fixed", 400, 0), ("fixed", 800, 0), ("heading", 400, 0), ("fixed", 400, 80)}
RUN_ID = re.compile(r"^[rs]\d{3,}$")


def results_problems(text: str, records: dict, cases_of) -> list:
    """Problems found when results.md is read against the learner's own screen records. records maps run id to record."""
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and RUN_ID.match(cells[1]):
            rows.append(cells)
    if not rows:
        return ["results.md has no screen table"]
    problems, seen = [], set()
    for label, rid, recall, tokens, facts in (r[:5] for r in rows):
        rec = records.get(rid)
        if rec is None or rec.get("kind") != "screen":
            problems.append(f"{rid} is not one of your screen records")
            continue
        cfg = rec["config"]
        seen.add((cfg["chunker"], cfg["chunk_size"], cfg["overlap"]))
        o = rec["overall"]
        value = float(recall.rstrip("%")) / (100 if recall.endswith("%") else 1)
        if abs(value - o["context_fact_recall"]) > 0.0006:
            problems.append(f"{rid}: context fact recall {recall} but the record says {o['context_fact_recall']}")
        if abs(int(float(tokens.replace(",", ""))) - o["context_tokens"]) > 1:
            problems.append(f"{rid}: context tokens {tokens} but the record says {o['context_tokens']}")
        if int(facts) != o["facts"]:
            problems.append(f"{rid}: {facts} key facts but the record says {o['facts']}")
    if seen != EXPECTED:
        problems.append("the five rows must be fixed 200, 400, 800, heading 400 and fixed 400 with overlap 80")
    for key, slice_name in (("split table case", "table"), ("lost heading case", "far-from-heading")):
        m = re.search(rf"^{key}:\s*(q-\d+)", text, re.M | re.I)
        if not m:
            problems.append(f"the line '{key}: q-NNN' is missing")
        elif not any(m.group(1) == c["id"] and slice_name in c["slices"] for r in rows for c in cases_of(r[1])):
            problems.append(f"{m.group(1)} is not a {slice_name} question in your screens")
    if not re.search(r"^candidate:\s*\S+", text, re.M | re.I):
        problems.append("the line 'candidate: <setting>' is missing")
    return problems


def _fixture():
    def rec(chunker, size, overlap, recall):
        return {"kind": "screen", "config": {"chunker": chunker, "chunk_size": size, "overlap": overlap},
                "overall": {"context_fact_recall": recall, "context_tokens": 1500, "facts": 27}}
    records = {"s001": rec("fixed", 200, 0, 0.5), "s002": rec("fixed", 400, 0, 0.6), "s003": rec("fixed", 800, 0, 0.7),
               "s004": rec("heading", 400, 0, 0.8), "s005": rec("fixed", 400, 80, 0.65)}
    cases = {rid: [{"id": "q-017", "slices": ["table"]}, {"id": "q-052", "slices": ["far-from-heading"]}] for rid in records}
    text = "| Setting | Screen run | Context fact recall | Context tokens | Key facts |\n|---|---|---|---|---|\n"
    for label, rid in (("fixed 200", "s001"), ("fixed 400", "s002"), ("fixed 800", "s003"), ("heading 400", "s004"), ("overlap 80", "s005")):
        text += f"| {label} | {rid} | {records[rid]['overall']['context_fact_recall']} | 1500 | 27 |\n"
    text += "\nsplit table case: q-017\nlost heading case: q-052\ncandidate: heading 400\n"
    return text, records, (lambda rid: cases[rid])


def test_the_results_checker_on_fixed_records():
    text, records, cases_of = _fixture()
    assert results_problems(text, records, cases_of) == []
    assert results_problems(text.replace("| 0.8 |", "| 0.9 |"), records, cases_of)                       # a recall that differs from the record
    assert results_problems(text.replace("q-017", "q-052", 1), records, cases_of)                         # a case that is not a table question
    assert results_problems(text.replace("s005", "s099"), records, cases_of)                              # a record that does not exist
    assert results_problems("# Results\n\nRun this part to write this file.\n", records, cases_of) == ["results.md has no screen table"]


@pytest.mark.skipif(is_reference_tree(), reason="the reference tree holds no learner screens; the checker is tested above")
def test_results_table():
    from harness.records import all_runs, load_results
    results = HERE / "results.md"
    text = results.read_text(encoding="utf-8") if results.exists() else ""
    records = {r["run_id"]: r for r in all_runs()}
    problems = results_problems(text, records, lambda rid: load_results(rid))
    assert not problems, "; ".join(problems)
