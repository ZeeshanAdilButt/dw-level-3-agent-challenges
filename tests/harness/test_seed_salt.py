"""Repeated runs sample independently: every run salts the model seeds with its run id, and records the salt."""
from conftest import cli
from harness.util import read_json, read_jsonl

from app.model import _seed

SET = ["--set", "model_path=stub"]


def test_the_seed_depends_on_the_salt_and_is_stable_for_one_salt():
    assert _seed("q-001:s1", 1, "r001") == _seed("q-001:s1", 1, "r001")          # a replay of the same run id is reproducible
    assert _seed("q-001:s1", 1, "r001") != _seed("q-001:s1", 1, "r002")          # another run draws another seed
    assert _seed("q-001:s1", 1) == _seed("q-001:s1", 1, "")                       # no salt (the live app) keeps the old seed


def test_repeat_runs_salt_every_case_with_their_own_run_id(repo):
    cli(repo, "run", "--pack", "mini", *SET, "--repeat", "2", check=True)
    for rid in ("r001", "r002"):
        assert read_json(repo / "runs" / rid / "run.json")["seed_salt"] == rid
        salts = {h for row in read_jsonl(repo / "runs" / rid / "raw.jsonl") for st in row["steps"]
                 for h in st["eval"].get("rule_hits") or [] if h.startswith("seed_salt:")}
        assert salts == {f"seed_salt:{rid}"}
