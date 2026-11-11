import json

import pytest

from conftest import write_run

pytestmark = pytest.mark.invariant


def test_empty_runs_folder(client):
    body = client.get("/api/runs").json()
    assert body["runs"] == [] and body["kept"] is None and body["confirmations"] == []


def test_list_and_get_a_run_with_its_cases(client, runs_dir):
    write_run(runs_dir, "r-001", totals={"answer_success": {"value": 0.5, "n": 2}},
              cases=[{"id": "q-001", "passed": True}, {"id": "q-002", "passed": False}])
    write_run(runs_dir, "r-002", parent="r-001", change="chunk_size: 400 -> 800")
    (runs_dir / "kept.json").write_text(json.dumps({"run_id": "r-002"}))
    (runs_dir / "confirm-r031.json").write_text(json.dumps({"best": {"answer_success": 0.6}}))
    listing = client.get("/api/runs").json()
    assert [r["id"] for r in listing["runs"]] == ["r-001", "r-002"]
    assert listing["kept"] == "r-002" and listing["confirmations"] == ["confirm-r031"]
    one = client.get("/api/runs/r-001").json()
    assert one["run"]["totals"]["answer_success"]["n"] == 2 and len(one["cases"]) == 2
    assert client.get("/api/runs/r-001?cases=0").json()["cases"] == []
    assert client.get("/api/runs/r-002").json()["cases"] == []
    conf = client.get("/api/runs/confirm-r031").json()
    assert conf["confirmation"]["best"]["answer_success"] == 0.6


def test_unknown_and_hostile_ids_are_refused(client, runs_dir, tmp_path):
    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "run.json").write_text("{}")
    for bad in ["nope", "..", "%2e%2e", "..%2fsecret", "%2e%2e%2fsecret", "a%00b", "confirm-..%2fsecret", "ref.."]:
        assert client.get(f"/api/runs/{bad}").status_code in (400, 404), bad


def test_a_broken_run_file_is_skipped_not_fatal(client, runs_dir):
    write_run(runs_dir, "r-001")
    (runs_dir / "r-bad").mkdir()
    (runs_dir / "r-bad" / "run.json").write_text("{not json")
    assert [r["id"] for r in client.get("/api/runs").json()["runs"]] == ["r-001"]


def test_reference_runs_are_listed_only_when_asked(client):
    assert client.get("/api/runs").json()["source"] == "runs"
    assert client.get("/api/runs?source=reference").json()["source"] == "reference"


def test_a_reference_run_folder_can_be_a_run_itself(tmp_path):
    from fastapi.testclient import TestClient
    from app.adapters.chat import create_app
    from conftest import ROOT
    root = tmp_path / "root"
    (root / "reference-runs" / "lab1").mkdir(parents=True)
    (root / "reference-runs" / "lab1" / "run.json").write_text(json.dumps({"run_id": "lab1-ref"}))
    (root / "reference-runs" / "lab1" / "cases.jsonl").write_text(json.dumps({"id": "q-001"}) + "\n")
    c = TestClient(create_app(root=root, runs_dir=tmp_path / "none", agent_factory=lambda: None))
    ids = [r["id"] for r in c.get("/api/runs?source=reference").json()["runs"]]
    assert ids == ["ref.lab1"]
    assert c.get("/api/runs/ref.lab1").json()["cases"] == [{"id": "q-001"}]


def test_the_api_never_writes(client, runs_dir):
    write_run(runs_dir, "r-001")
    before = sorted(p.name for p in runs_dir.rglob("*"))
    for path in ["/api/runs", "/api/runs/r-001", "/health"]:
        client.get(path)
    assert sorted(p.name for p in runs_dir.rglob("*")) == before
    assert client.post("/api/runs", json={}).status_code in (404, 405)
    assert client.delete("/api/runs/r-001").status_code in (404, 405)


def test_prices_table_is_served(client):
    prices = client.get("/api/config/prices").json()
    assert prices["date"] == "2026-11-06"
    assert prices["models"]["claude-haiku-5-5"]["input"] == 0.10
    assert prices["models"]["claude-haiku-5-5"]["output"] == 0.50
    assert prices["models"]["qwen3:4b-instruct"]["input"] == 0
