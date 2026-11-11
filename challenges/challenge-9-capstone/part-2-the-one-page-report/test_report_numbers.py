"""Capstone part 2: the report. Layer 1 checks the checks on fixed text and fixed files (and the template). Layer 2 runs the
same checks on YOUR REPORT.md, in a learner repository only (one with LAB-LOG.md at its root).

On the starter, layer 2 fails with: AssertionError: report has no linked numbers
Punctuation is not tested: a range such as 60-70 is fine. The report is judged on its numbers and its honesty.
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.report_check import ANY_LINK, MAX_WORDS, check_text, word_count  # noqa: E402

LEARNER_REPO = (ROOT / "LAB-LOG.md").exists()
TEMPLATE = ROOT / "challenges" / "challenge-9-capstone" / "REPORT.template.md"
SECTIONS = ["The best setup", "Each kept change", "What did not work", "Security pass rate by family",
            "Cost per answer and p95", "Public score against my own ten questions", "Limits of this evaluation",
            "How email and phone would plug in"]
COMMENT = re.compile(r"<!--.*?-->", re.S)
# a measured number written as plain text: a percentage, a dollar amount, or a time in ms or seconds
MEASURED = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?\s?%|\$\d[\d.,]*|\d+(?:\.\d+)?\s?(?:ms|s)\b)")


def unlinked_measurements(md: str) -> list:
    text = COMMENT.sub(" ", md)
    text = ANY_LINK.sub(" ", text)                       # a number inside a link is a linked number
    return MEASURED.findall(text)


def sections_in_order(md: str) -> list:
    """Return the required sections that are missing or out of order."""
    headings = [h.strip() for h in re.findall(r"^##\s+(?:\d+\.\s*)?(.+)$", COMMENT.sub(" ", md), re.M)]
    missing, last = [], -1
    for want in SECTIONS:
        idx = next((i for i, h in enumerate(headings) if h.startswith(want)), None)
        if idx is None or idx < last:
            missing.append(want)
        else:
            last = idx
    return missing


def check_report(md: str, root: Path) -> None:
    problems, n_links, words = check_text(md, root)
    assert n_links > 0, "report has no linked numbers"
    assert not problems, problems
    assert words <= MAX_WORDS
    assert not sections_in_order(md), "missing or out of order: " + ", ".join(sections_in_order(md))
    assert not unlinked_measurements(md), "numbers from runs must be links, but these are plain text: " + ", ".join(unlinked_measurements(md))


# ---- layer 1: fixed text and fixed files --------------------------------------------------------------------------

@pytest.fixture
def files(tmp_path):
    (tmp_path / "runs" / "r012").mkdir(parents=True)
    (tmp_path / "runs" / "confirm-r031.json").write_text(json.dumps({"best": {"answer_success": {"value": 0.64, "n": 100}}}), encoding="utf-8")
    (tmp_path / "runs" / "r012" / "run.json").write_text(
        json.dumps({"totals": {"latency_p95_ms": {"value": 9000.0, "n": 40}, "cost_p50": {"value": 0.00035, "n": 40}}}), encoding="utf-8")
    return tmp_path


def fill(body: str) -> str:
    out = []
    for i, name in enumerate(SECTIONS, 1):
        out.append(f"## {i}. {name}\n\n" + (body if i == 2 else "Plain text.") + "\n")
    return "# Report\n\n" + "\n".join(out)


def test_a_linked_number_that_matches_its_file_passes(files):
    md = fill("[64% answer success](runs/confirm-r031.json#best.answer_success), p95 [9000 ms](runs/r012/run.json#totals.latency_p95_ms), "
              "cost [0.00035 dollars](runs/r012/run.json#totals.cost_p50).")
    check_report(md, files)


def test_a_number_that_differs_from_its_file_is_caught(files):
    md = fill("[65% answer success](runs/confirm-r031.json#best.answer_success).")
    with pytest.raises(AssertionError, match="65%"):
        check_report(md, files)


def test_a_link_to_a_missing_file_or_metric_is_caught(files):
    with pytest.raises(AssertionError, match="does not exist"):
        check_report(fill("[64% answer success](runs/confirm-r099.json#best.answer_success)."), files)
    with pytest.raises(AssertionError, match="no 'best.recall'"):
        check_report(fill("[64% recall](runs/confirm-r031.json#best.recall)."), files)


def test_a_plain_text_measurement_is_caught(files):
    md = fill("[64% answer success](runs/confirm-r031.json#best.answer_success) and it improved by 12% overall.")
    with pytest.raises(AssertionError, match="12%"):
        check_report(md, files)


def test_settings_and_design_counts_are_plain_text(files):
    md = fill("[64% answer success](runs/confirm-r031.json#best.answer_success) with temperature 0.2, 8 attacks per family and top_k 5 on 2026-11-01.")
    check_report(md, files)
    assert unlinked_measurements(md) == []


def test_a_report_with_no_links_has_no_linked_numbers(files):
    with pytest.raises(AssertionError, match="no linked numbers"):
        check_report(fill("It improved a lot."), files)


def test_a_missing_section_is_caught(files):
    md = fill("[64% answer success](runs/confirm-r031.json#best.answer_success).").replace("## 7. Limits of this evaluation", "## 7. Notes")
    with pytest.raises(AssertionError, match="Limits"):
        check_report(md, files)


def test_more_than_600_words_is_caught(files):
    md = fill("[64% answer success](runs/confirm-r031.json#best.answer_success). " + "word " * 600)
    with pytest.raises(AssertionError, match="600"):
        check_report(md, files)


def test_the_template_has_every_section_in_order_and_fits_the_page():
    md = TEMPLATE.read_text(encoding="utf-8")
    assert sections_in_order(md) == []
    assert word_count(md) <= MAX_WORDS
    assert "[64% answer success](runs/confirm-r031.json#best.answer_success)" in md        # the link syntax is shown
    assert "\u2014" not in md and "\u2013" not in md


def test_the_template_has_no_linked_numbers_yet():
    problems, n_links, _ = check_text(COMMENT.sub(" ", TEMPLATE.read_text(encoding="utf-8")), ROOT)
    assert n_links == 0 and problems == []                 # so the starter fails layer 2 with "report has no linked numbers"


# ---- layer 2: your REPORT.md (learner repositories only) ----------------------------------------------------------

@pytest.mark.skipif(not LEARNER_REPO, reason="runs in a learner repository only")
def test_my_report_numbers_are_linked_and_match_my_runs():
    check_report((ROOT / "REPORT.md").read_text(encoding="utf-8"), ROOT)
