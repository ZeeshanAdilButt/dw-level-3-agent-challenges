"""Load cases and normalise them to steps (decision C4).

A case in questions.jsonl, attacks.jsonl (or safety.jsonl) either has `steps`, or the old `turns` list that
expands to steps with the case's principal. Principals come from the fixture (`fixture.principals[].id`) when a
step names one, or inline as in version 1 (the id is then built from the account or the role).
"""
import json
from pathlib import Path

from app.types import principal_id  # noqa: F401  (one rule for the harness and the chat adapter's test header)

from . import paths
from .util import read_json, read_jsonl, sha


def resolve_principal(ref, fixture: dict, default: dict = None) -> dict:
    """A principal dict {id, role, verified, account_id} from an id, an inline dict or the case default."""
    if isinstance(ref, str):
        for p in (fixture or {}).get("principals") or []:
            if p.get("id") == ref:
                ref = p
                break
        else:
            raise ValueError(f"principal '{ref}' is not in the fixture")
    p = dict(ref or default or {"role": "prospect", "verified": False, "account_id": None})
    if p.get("id") and not ({"role", "verified"} & set(p)):
        for fp in (fixture or {}).get("principals") or []:
            if fp.get("id") == p["id"]:
                p = {**fp, **p}
    p.setdefault("role", "customer")
    p["verified"] = bool(p.get("verified", False))
    p.setdefault("account_id", None)
    p["id"] = principal_id(p)
    return p


def normalize_case(raw: dict, kind: str, fixture: dict = None) -> dict:
    """Return the spec the graders and the runner use. Keeps every field the graders read."""
    case_principal = resolve_principal(raw.get("principal"), fixture) if raw.get("principal") is not None else None
    steps = []
    if raw.get("steps"):
        by_id, by_req = {}, {}
        for i, s in enumerate(raw["steps"], start=1):
            sid = s.get("id") or f"s{i}"
            text = s.get("text")
            req = s.get("request_id")
            if s.get("repeat_of"):
                prev = by_id.get(s["repeat_of"]) or by_req.get(s["repeat_of"])  # a step id or a request id
                if prev is None:
                    raise ValueError(f"{raw['id']}: step {sid} repeats unknown step {s['repeat_of']}")
                text, req = text or prev["text"], prev["request_id"]
            step = {"id": sid, "text": text, "principal": resolve_principal(s.get("principal"), fixture, case_principal),
                    "conversation": s.get("conversation") or "c1", "request_id": req or f"{raw['id']}:{sid}",
                    "repeat_of": s.get("repeat_of"), "expect": dict(s.get("expect") or {})}
            by_id[sid] = step
            if s.get("request_id"):
                by_req[s["request_id"]] = step
            steps.append(step)
    else:
        turns = raw.get("turns") or []
        for i, t in enumerate(turns, start=1):
            exp = {"action": raw.get("expected_action")} if i == len(turns) and raw.get("expected_action") else {}
            steps.append({"id": f"s{i}", "text": t, "principal": case_principal or resolve_principal(None, fixture),
                          "conversation": "c1", "request_id": f"{raw['id']}:s{i}", "repeat_of": None, "expect": exp})
    spec = {k: raw[k] for k in raw if k not in ("turns", "steps", "principal")}
    spec.update({"kind": kind, "steps": steps, "principal": case_principal or (steps[0]["principal"] if steps else None)})
    spec.setdefault("slices", [])
    spec.setdefault("key_facts", [])
    spec.setdefault("gold_sources", [])
    spec.setdefault("needs", [])
    spec["must_pass"] = bool(raw.get("must_pass"))
    return spec


def load_fixture(pack_dir) -> dict:
    return read_json(Path(pack_dir) / "tools" / "fixture.json", {}) or {}


def load_context(pack_dir) -> dict:
    """Canaries and confidential facts for the security checks: {"canaries": [...], "facts": {id: fact}}."""
    raw = read_json(Path(pack_dir) / "eval" / "confidential.json", {}) or {}
    return {"canaries": list(raw.get("canaries") or []), "facts": {f["id"]: f for f in raw.get("facts") or []}}


def qset_version(pack_dir) -> str:
    ev = Path(pack_dir) / "eval"
    blob = "".join((ev / n).read_text(encoding="utf-8") for n in ("questions.jsonl", "attacks.jsonl", "safety.jsonl")
                   if (ev / n).exists())
    return sha(blob)[:12]


def load_cases(pack: str, smoke: bool = False, slice_name: str = None, pack_dir=None) -> list:
    pd = Path(pack_dir) if pack_dir else paths.pack_dir(pack)
    fixture = load_fixture(pd)
    ev = pd / "eval"
    rows = []
    if smoke:
        for r in read_jsonl(ev / "smoke.jsonl"):
            rows.append((r, "attack" if str(r.get("id", "")).startswith("a-") else "question"))
    else:
        rows += [(r, "question") for r in read_jsonl(ev / "questions.jsonl")]
        rows += [(r, "attack") for r in read_jsonl(ev / "attacks.jsonl")]
        rows += [(r, "safety") for r in read_jsonl(ev / "safety.jsonl")]
    cases = [normalize_case(r, k, fixture) for r, k in rows]
    if slice_name:
        cases = [c for c in cases if slice_name in c["slices"] or slice_name == c.get("family")]
    return cases


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)
