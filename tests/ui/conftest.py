"""Fixtures for the UI and tooling tests. They use a fake agent, so they pass whether or not the core is finished."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.adapters.chat import create_app  # noqa: E402
from app.types import EvalBlock, Reply  # noqa: E402


def pytest_configure(config):
    config.addinivalue_line("markers", "invariant: passes on the starter as well as on the reference tree")


class FakeAgent:
    """Records the messages it gets and answers the same way every time."""

    def __init__(self):
        self.seen = []

    def handle(self, msg):
        self.seen.append(msg)
        block = EvalBlock(raw_reply="fake reply", ranked_hit_ids=["doc-x#0"], delivered_doc_ids=["doc-pricing-table"])
        return Reply(text="fake reply", citations=["doc-pricing-table"], actions=[], pending=None, handoff=None,
                     usage=[], cost_usd=0.0, latency_ms=1.0, trace_id="t-1", eval=block)


@pytest.fixture
def agent():
    return FakeAgent()


@pytest.fixture
def runs_dir(tmp_path):
    d = tmp_path / "runs"
    d.mkdir()
    return d


@pytest.fixture
def client(agent, runs_dir, monkeypatch):
    monkeypatch.delenv("DW_TEST_MODE", raising=False)
    monkeypatch.delenv("DW_EXAM_TOKEN", raising=False)
    monkeypatch.setenv("DW_COMMIT", "test-commit")
    return TestClient(create_app(root=ROOT, runs_dir=runs_dir, agent_factory=lambda: agent))


def fixture_email(pack="quillon", role="customer"):
    """One fixture email of a given role, read from the pack's own fixture."""
    from app.adapters.chat import load_principals
    principals, emails = load_principals(ROOT, pack)
    for email, pid in sorted(emails.items()):
        if principals[pid].role == role:
            return email, principals[pid]
    raise AssertionError(f"no {role} email in the {pack} fixture")


CODE_RE = re.compile(r"one-time code for (\S+): (\d{6})")


def read_code(capsys, email):
    out = capsys.readouterr().out
    m = CODE_RE.search(out)
    assert m and m.group(1) == email, out
    return m.group(2)


def sign_in(client, capsys, email):
    """Run the sign-in flow the way a person does: ask for a code, read it from the server log, send it back."""
    assert client.post("/api/signin", json={"email": email}).status_code == 200
    code = read_code(capsys, email)
    return client.post("/api/verify", json={"email": email, "code": code})


def write_run(runs_dir, run_id, parent=None, change=None, totals=None, cases=None, **extra):
    d = runs_dir / run_id
    d.mkdir()
    run = {"run_id": run_id, "parent": parent, "change": change, "totals": totals or {}, **extra}
    (d / "run.json").write_text(json.dumps(run), encoding="utf-8")
    if cases is not None:
        (d / "cases.jsonl").write_text("\n".join(json.dumps(c) for c in cases) + "\n", encoding="utf-8")
    return d
