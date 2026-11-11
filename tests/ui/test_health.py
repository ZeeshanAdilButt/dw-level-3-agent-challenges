import json
import subprocess

import pytest

from conftest import write_run

pytestmark = pytest.mark.invariant


def head_or_env():
    """What /health must report: git HEAD when the tree is a repository, else DW_COMMIT (the test sets test-commit)."""
    from conftest import ROOT
    if not (ROOT / ".git").exists():
        return "test-commit"
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"


def test_health_has_the_four_fields_the_examiner_reads(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["commit"] == head_or_env()                    # DW_COMMIT cannot override a real repository's HEAD
    assert isinstance(body["fingerprint"], str) and body["fingerprint"]
    assert isinstance(body["model"], str) and body["model"]


def test_fingerprint_is_recomputed_from_the_kept_runs_manifest(client, runs_dir):
    from harness.util import sha
    assert client.get("/health").json()["fingerprint"] == "none"
    manifest = {"corpus_hash": "c1", "prompts": "p1", "code": {"commit": "abc"}}
    honest = sha(manifest)[:16]                                # what harness/fingerprint.py writes
    write_run(runs_dir, "r-001", fingerprint=honest, manifest={**manifest, "fingerprint": honest})
    (runs_dir / "kept.json").write_text(json.dumps({"run_id": "r-001"}))
    assert client.get("/health").json()["fingerprint"] == honest
    write_run(runs_dir, "r-002", fingerprint="f1f1f1", manifest={**manifest, "fingerprint": "f1f1f1"})   # an edited string
    (runs_dir / "kept.json").write_text(json.dumps(["r-001", "r-002"]))
    assert client.get("/health").json()["fingerprint"] == honest
    write_run(runs_dir, "r-003", fingerprint="f1f1f1")         # nothing to recompute from
    (runs_dir / "kept.json").write_text(json.dumps({"run_id": "r-003"}))
    assert client.get("/health").json()["fingerprint"] == "none"


def test_health_works_while_the_core_is_missing_or_broken(runs_dir):
    from fastapi.testclient import TestClient
    from app.adapters.chat import CoreUnavailable, create_app
    from conftest import ROOT

    def broken():
        raise CoreUnavailable("not built yet")

    c = TestClient(create_app(root=ROOT, runs_dir=runs_dir, agent_factory=broken))
    assert c.get("/health").status_code == 200
    assert c.get("/mock-state").status_code == 503


def test_fingerprint_says_edited_when_the_kept_record_no_longer_matches_its_digest(client, runs_dir):
    from harness.records import record_digest
    from harness.util import sha
    manifest = {"corpus_hash": "c1", "prompts": "p1", "code": {"commit": "abc"}}
    honest = sha(manifest)[:16]
    rows = [{"case_id": "q-1", "passed": False, "steps": [{"reply": {"text": "I do not know."}}]}]
    run = {"run_id": "r-001", "parent": None, "change": None, "totals": {}, "manifest": {**manifest, "fingerprint": honest}}
    write_run(runs_dir, "r-001", cases=rows, manifest=run["manifest"], digest=record_digest(run, rows))
    (runs_dir / "kept.json").write_text(json.dumps({"run_id": "r-001"}))
    assert client.get("/health").json()["fingerprint"] == honest
    rows[0]["passed"] = True                                                       # a manufactured pass
    (runs_dir / "r-001" / "cases.jsonl").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    assert client.get("/health").json()["fingerprint"] == "edited"


def test_health_says_whether_the_served_settings_are_the_kept_runs(client, runs_dir):
    from app.adapters.chat import load_flat_settings
    from conftest import ROOT
    assert client.get("/health").json()["settings_match"] is None                  # no kept run yet
    served = load_flat_settings(ROOT)
    write_run(runs_dir, "r-001", settings=dict(served), manifest={"code": {}})
    write_run(runs_dir, "r-002", settings={**served, "top_k": served["top_k"] + 1}, manifest={"code": {}})
    (runs_dir / "kept.json").write_text(json.dumps({"run_id": "r-001"}))
    assert client.get("/health").json()["settings_match"] is True
    (runs_dir / "kept.json").write_text(json.dumps({"run_id": "r-002"}))
    assert client.get("/health").json()["settings_match"] is False
