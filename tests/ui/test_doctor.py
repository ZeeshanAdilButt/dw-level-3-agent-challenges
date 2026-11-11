import sys

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import doctor  # noqa: E402

pytestmark = pytest.mark.invariant


def test_path_choice_uses_the_median_against_eight_seconds():
    assert doctor.choose_path([2.0, 3.0, 4.0, 5.0, 6.0])[0] == "local"
    assert doctor.choose_path([9.0, 9.5, 10.0, 11.0, 12.0])[0] == "hosted"
    assert doctor.choose_path([8.0, 8.0, 8.0])[0] == "local"            # at the limit is allowed
    # one slow first call (the model loading) does not decide it; the median does
    assert doctor.choose_path([30.0, 3.0, 3.0, 3.0, 3.0])[0] == "local"
    assert doctor.choose_path([])[0] == "hosted"


def test_model_names_match_the_way_ollama_lists_them():
    names = ["qwen3:4b-instruct", "nomic-embed-text:latest"]
    assert doctor.model_present("qwen3:4b-instruct", names)
    assert doctor.model_present("nomic-embed-text", names)
    assert not doctor.model_present("qwen3:8b", names)
    assert not doctor.model_present("qwen3:4b-instruct", ["qwen3:4b"])


def test_fts5_and_python_checks_pass_here():
    assert doctor.check_fts5().ok
    assert doctor.check_python().ok


def test_doctor_runs_without_a_model(capsys, tmp_path):
    code = doctor.main(["--skip-model", "--out", str(tmp_path / "doctor.json")])
    out = capsys.readouterr().out
    assert code == 0 and "SQLite FTS5" in out and "Required checks passed" in out
    import json
    receipt = json.loads((tmp_path / "doctor.json").read_text(encoding="utf-8"))
    assert receipt["required_checks_passed"] is True and receipt["model_timing"]["skipped"] is True
    assert any(c["name"] == "SQLite FTS5" or "FTS5" in c["name"] for c in receipt["checks"])
