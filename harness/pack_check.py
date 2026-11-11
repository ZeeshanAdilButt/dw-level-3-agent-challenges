"""python -m harness pack-check <pack>: check a pack copy (the one a learner holds, or the reference's).

Everything here is checkable from the pack folder alone: documents, public questions and attacks, the smoke set,
the fixture and the confidential facts. Fact sheets (reference only) are checked by tools/check_facts.py.
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

from . import paths
from .canonical import canonical_text, sha256_text
from .cases import load_cases, load_fixture
from .graders.text import contains_canary
from .util import read_json, read_jsonl

FAMILIES = {"doc-injection", "message-injection", "other-person", "internal-content", "system-prompt", "domain-harm"}
DASHES = ("\u2014", "\u2013")
ACTIONS = {"answer", "tool", "clarify", "handoff", "refuse"}


def load_families(root: Path) -> set:
    f = root / "config" / "ids.yaml"
    if f.exists():
        d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        return set(d.get("attack_families") or d.get("families") or FAMILIES)
    return FAMILIES


def _is_small_copy(pd: Path) -> bool:
    return any(pd.name == c + s for c in ("quillon", "juniper", "saltmarsh") for s in ("-mine", "-practice"))


def check_pack(pack: str, pack_dir: Path = None, root: Path = None) -> list:
    """Return a list of (status, message) with status "FAIL" or "WARN" (empty when the pack is clean)."""
    pd = Path(pack_dir or paths.pack_dir(pack))
    root = root or paths.root()
    out = []
    fail = lambda m: out.append(("FAIL", m))  # noqa: E731
    warn = lambda m: out.append(("WARN", m))  # noqa: E731
    if not pd.exists():
        return [("FAIL", f"no pack folder {pd}")]
    docs = {}
    for f in sorted((pd / "corpus").glob("*.md")) if (pd / "corpus").exists() else []:
        raw = f.read_text(encoding="utf-8")
        parts = raw.split("---", 2)
        if len(parts) < 3:
            fail(f"{f.name}: no front matter")
            continue
        try:
            meta = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            fail(f"{f.name}: front matter is not valid YAML")
            continue
        if meta.get("doc_id") != f.stem:
            fail(f"{f.name}: doc_id '{meta.get('doc_id')}' does not match the file name")
        for k in ("doc_id", "title"):
            if not meta.get(k):
                fail(f"{f.name}: front matter lacks {k}")
        docs[meta.get("doc_id")] = {"meta": meta, "body": parts[2].strip(), "raw": raw, "canon": canonical_text(raw)}
        if any(d in raw for d in DASHES):
            fail(f"{f.name}: contains an em or en dash")
    if not docs:
        fail("no documents in corpus/")
    for did, d in docs.items():
        for link in d["meta"].get("links") or []:
            if link not in docs:
                fail(f"{did}: links to unknown document {link}")
    ev = pd / "eval"
    q = read_jsonl(ev / "questions.jsonl")
    a = read_jsonl(ev / "attacks.jsonl")
    sm = read_jsonl(ev / "smoke.jsonl")
    small = _is_small_copy(pd)       # <co>-mine and <co>-practice may hold fewer rows than the full 100, 48 and 40
    for name, rows, want in (("questions", q, 100), ("attacks", a, 48), ("smoke", sm, 40)):
        if small:
            if len(rows) > want or (name == "questions" and not rows):
                fail(f"{name}.jsonl has {len(rows)} rows; a small copy holds at most {want}" + (" and at least one" if name == "questions" else ""))
        elif len(rows) != want:
            fail(f"{name}.jsonl has {len(rows)} rows, expected {want}")
        ids = [r.get("id") for r in rows]
        if len(set(ids)) != len(ids):
            fail(f"{name}.jsonl has duplicate ids")
    if sm and not small and (sum(1 for r in sm if str(r["id"]).startswith("q-")) != 30 or sum(1 for r in sm if str(r["id"]).startswith("a-")) != 10):
        fail("smoke.jsonl must hold 30 questions and 10 attacks")
    if sm and small and any(not str(r["id"]).startswith(("q-", "a-")) for r in sm):
        fail("smoke.jsonl ids must start with q- or a-")
    known = {r["id"]: r for r in q + a}
    for r in sm:
        if r.get("id") in known and known[r["id"]] != r:
            warn(f"smoke case {r['id']} differs from the full set's copy")
    try:
        cases = load_cases(pack, pack_dir=pd)
    except ValueError as e:
        fail(str(e))
        cases = []
    fixture = load_fixture(pd)
    fam = load_families(root)
    for c in cases:
        for src in c["gold_sources"]:
            if src not in docs:
                fail(f"{c['id']}: gold source {src} is not a document")
        if c["kind"] == "question":
            if c.get("expected_action") not in ACTIONS:
                fail(f"{c['id']}: expected_action '{c.get('expected_action')}' is not one of {sorted(ACTIONS)}")
            for kf in c["key_facts"]:
                if not kf.get("forms"):
                    fail(f"{c['id']}: key fact {kf.get('id')} has no forms")
                    continue
                blob = "\n".join(docs[s]["body"].lower() for s in c["gold_sources"] if s in docs)
                if c["gold_sources"] and not any(str(f).lower() in blob for f in kf["forms"]):
                    fail(f"{c['id']}: key fact {kf.get('id')} does not occur in its gold sources")
            for sp in c.get("gold_spans") or []:
                d = docs.get(sp.get("doc"))
                if not d:
                    fail(f"{c['id']}: gold span names unknown document {sp.get('doc')}")
                    continue
                if sha256_text(d["canon"]) != sp.get("doc_sha256"):
                    fail(f"{c['id']}: gold span hash does not match {sp['doc']} (the document changed)")
                elif not (0 <= sp["start"] < sp["end"] <= len(d["canon"])):
                    fail(f"{c['id']}: gold span offsets lie outside {sp['doc']}")
        else:
            if c.get("family") not in fam:
                fail(f"{c['id']}: attack family '{c.get('family')}' is not in the list of families")
            if c.get("planted_doc") and c["planted_doc"] not in docs:
                fail(f"{c['id']}: planted_doc {c['planted_doc']} is not a document")
        seen = set()
        for st in c["steps"]:
            if st["principal"].get("account_id") and fixture and fixture.get("accounts") is not None:
                known_accounts = {x.get("account_id") for x in fixture["accounts"]} | {x.get("account_id") for x in fixture.get("principals") or []}
                if st["principal"]["account_id"] not in known_accounts:
                    warn(f"{c['id']}: account {st['principal']['account_id']} is not in the fixture")
            seen.add(st["id"])
    conf = read_json(ev / "confidential.json", {}) or {}
    for canary in conf.get("canaries") or []:
        holders = [d for d, x in docs.items() if contains_canary(x["raw"], canary)]
        if len(holders) != 1:
            fail(f"canary '{canary}' appears in {len(holders)} documents (expected exactly one)")
        elif docs[holders[0]]["meta"].get("audience") == "public":
            fail(f"canary '{canary}' is in a public document ({holders[0]})")
    for f in list(ev.glob("*")) if ev.exists() else []:
        if f.suffix in (".jsonl", ".json", ".md") and any(d in f.read_text(encoding="utf-8") for d in DASHES):
            fail(f"eval/{f.name}: contains an em or en dash")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness pack-check")
    ap.add_argument("pack")
    a = ap.parse_args(argv)
    res = check_pack(a.pack)
    for status, msg in res:
        print(f"  {status} {msg}")
    fails = sum(1 for s, _ in res if s == "FAIL")
    print(f"pack-check {a.pack}: " + ("clean" if not res else f"{fails} failure(s), {len(res) - fails} warning(s)"))
    return 1 if fails else 0
