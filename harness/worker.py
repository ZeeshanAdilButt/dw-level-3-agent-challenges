"""Executes cases and stores raw step results. Runs inside the snapshot (`python -m harness.worker`), or in
process for `--url` (the examiner's path). It grades nothing: graders read the stored results afterwards.

The in-process agent is built from `app.core.Agent`; DW_AGENT_FACTORY="module:function" replaces it (tests, the
stub path). The function takes (settings, pack_dir, mock) and returns an object with `handle(Message) -> Reply`.
"""
import argparse
import importlib
import json
import os
import queue
import threading
import time
import urllib.request
from dataclasses import asdict, is_dataclass
from pathlib import Path

from .retrieval_bridge import install_embedding_stats, offsets_table
from .util import now_iso, read_json, read_jsonl


class NullMock:
    """Stand-in when mock_api is not importable: no state, so state checks see an empty mock."""
    kind = "none"

    def __init__(self, *a, **k):
        pass

    def reset(self):
        pass

    def state(self):
        return {}


def make_mock(pack_dir, namespace):
    url = os.environ.get("MOCK_API_URL")
    try:
        if url:
            from mock_api import HttpMockClient  # type: ignore
            m = HttpMockClient(url, namespace)
        else:
            try:
                from mock_api import MockClient  # type: ignore
            except ImportError:
                from mock_api.client import MockClient  # type: ignore
            m = MockClient(Path(pack_dir), namespace)
        m.kind = type(m).__name__
        return m
    except ImportError:
        return NullMock()


def agent_factory():
    spec = os.environ.get("DW_AGENT_FACTORY")
    if spec:
        mod, fn = spec.split(":")
        return getattr(importlib.import_module(mod), fn)
    from app.core import Agent  # type: ignore
    return lambda settings, pack_dir, mock: Agent(settings, pack_dir, mock)


def _as_dict(x):
    if x is None or isinstance(x, dict):
        return x or {}
    return asdict(x) if is_dataclass(x) else dict(vars(x))


def split_reply(reply) -> tuple:
    """(reply dict without eval, eval dict) from a Reply object or the /api/chat JSON."""
    d = _as_dict(reply)
    ev = _as_dict(d.pop("eval", None))
    return d, ev


def call_with_timeout(fn, seconds):
    """Run fn in a daemon thread; return (value, error, timed_out)."""
    q = queue.Queue()

    def target():
        try:
            q.put((fn(), None))
        except Exception as e:  # recorded, not raised: one broken case must not stop the run
            q.put((None, f"{type(e).__name__}: {e}"))
    t = threading.Thread(target=target, daemon=True)
    t.start()
    try:
        value, err = q.get(timeout=seconds)
        return value, err, False
    except queue.Empty:
        return None, f"timeout after {seconds}s", True


def http_chat(url, step, principal, text, conversation_id, request_id, timeout):
    body = json.dumps({"request_id": request_id, "conversation_id": conversation_id, "text": text}).encode()
    headers = {"Content-Type": "application/json", "X-Test-Principal": json.dumps(principal)}
    if os.environ.get("DW_EXAM_TOKEN"):
        headers["X-Exam-Token"] = os.environ["DW_EXAM_TOKEN"]
    req = urllib.request.Request(url.rstrip("/") + "/api/chat", body, headers)
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def http_state(url):
    try:
        return json.load(urllib.request.urlopen(url.rstrip("/") + "/mock-state", timeout=10))
    except Exception:
        return {}


def _hosted_equivalent(usage: dict) -> float:
    """What this call would cost on the hosted path: the core's own figure, else priced here from config/prices.toml."""
    if usage.get("hosted_equivalent_usd") is not None:
        return float(usage["hosted_equivalent_usd"])
    try:
        from app.model import cost  # type: ignore
        return cost(usage.get("model") or "", usage.get("tokens_in", 0), usage.get("tokens_out", 0))[1]
    except Exception:
        return 0.0


def run_case(spec, settings, pack_dir, ns, factory, state_ref, timeout=120, url=None, offsets=None, docs=None):
    """Execute one case. `state_ref` is a dict {"agent": ..., "mock": ...} that lets one agent serve many cases."""
    from app.types import Message, principal_from_dict  # type: ignore
    started = time.time()
    rec = {"case_id": spec["id"], "kind": spec["kind"], "started_at": now_iso(), "steps": [], "has_reply": False,
           "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
           "calls": 0, "hosted_equivalent_usd": 0.0}
    mock = None
    agent = None
    if url:
        rec["state_before"] = http_state(url)
    else:
        mock = make_mock(pack_dir, ns)
        mock.reset()
        rec["state_before"] = mock.state()
        agent = state_ref.get("agent")
        if agent is not None and hasattr(agent, "set_mock"):
            agent.set_mock(mock)
        else:
            agent = factory(settings, pack_dir, mock)
            state_ref["agent"] = agent
    for st in spec["steps"]:
        conv = f"{spec['id']}:{st['conversation']}"
        p = st["principal"]
        t0 = time.time()
        if url:
            fn = lambda: http_chat(url, st, p, st["text"], conv, st["request_id"], timeout)  # noqa: E731
        else:
            msg = Message(request_id=st["request_id"], conversation_id=conv, principal=principal_from_dict(p), text=st["text"])
            fn = lambda: agent.handle(msg)  # noqa: E731
        value, err, timed_out = call_with_timeout(fn, timeout)
        reply, ev = split_reply(value) if value is not None else ({}, {})
        step = {"step_id": st["id"], "text": st["text"], "principal": p["id"], "conversation": conv,
                "request_id": st["request_id"], "reply": reply, "eval": ev, "error": err if not timed_out else None,
                "timeout": timed_out, "latency_ms": round((time.time() - t0) * 1000, 1),
                "state": http_state(url) if url else mock.state()}
        ids = list(dict.fromkeys((ev.get("ranked_hit_ids") or []) + (ev.get("expanded_evidence_ids") or [])
                                 + (ev.get("delivered_evidence_ids") or [])))
        if offsets:
            step["offsets"] = {i: offsets[i] for i in ids if i in offsets}
        if docs and spec["kind"] != "question":      # attack cases keep the delivered documents so leak_path can name the source
            step["delivered_docs"] = {d: docs[d].body for d in (ev.get("delivered_doc_ids") or []) if d in docs}
        if docs:
            step["cited_docs"] = {d: docs[d].body for d in (reply.get("citations") or []) if d in docs}
        rec["steps"].append(step)
        if reply:
            rec["has_reply"] = True
        for u in reply.get("usage") or ev.get("usage") or []:
            rec["tokens_in"] += u.get("tokens_in", 0)
            rec["tokens_out"] += u.get("tokens_out", 0)
            rec["calls"] += 1
            rec["hosted_equivalent_usd"] += _hosted_equivalent(u)
        rec["cost_usd"] += reply.get("cost_usd") or 0.0
        if timed_out:
            break
    rec["state_after"] = http_state(url) if url else mock.state()
    rec["ended_at"] = now_iso()
    rec["latency_ms"] = round((time.time() - started) * 1000, 1)
    rec["mock"] = "http" if url else getattr(mock, "kind", "MockClient")
    return rec


def execute(run_dir: Path, run_id: str, url=None, timeout=120, uncached_queries=True) -> dict:
    """Run every case in run_dir/specs.jsonl that is not yet in raw.jsonl; append results as they finish."""
    settings = read_json(run_dir / "settings.json")
    salt = (read_json(run_dir / "run.json", {}) or {}).get("seed_salt") or run_id
    old_salt = os.environ.get("DW_SEED_SALT")
    os.environ["DW_SEED_SALT"] = salt              # the model seeds of this run: independent of other runs, replayable by run id
    try:
        return _execute(run_dir, run_id, settings, url, timeout, uncached_queries)
    finally:
        if old_salt is None:
            os.environ.pop("DW_SEED_SALT", None)
        else:
            os.environ["DW_SEED_SALT"] = old_salt


def _execute(run_dir: Path, run_id: str, settings: dict, url, timeout, uncached_queries) -> dict:
    specs = read_jsonl(run_dir / "specs.jsonl")
    raw = run_dir / "raw.jsonl"
    done = {r["case_id"] for r in read_jsonl(raw)}
    pack_dir = Path(os.environ.get("DW_ROOT", ".")) / "packs" / settings["pack"]
    stats = install_embedding_stats(settings["embed_model"], uncached_queries) if settings["retriever"] in ("vector", "hybrid") else None
    docs, offsets = offsets_table(settings, pack_dir)
    factory = None if url else agent_factory()
    state_ref = {}
    with open(raw, "a", encoding="utf-8") as out:
        for spec in specs:
            if spec["id"] in done:
                continue
            rec = run_case(spec, settings, pack_dir, f"{run_id}-{spec['id']}", factory, state_ref, timeout, url, offsets, docs)
            out.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            out.flush()
    info = {"embedding_stats": stats}
    (run_dir / "worker.json").write_text(json.dumps(info), encoding="utf-8")
    return info


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness.worker")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--timeout", type=float, default=120)
    a = ap.parse_args(argv)
    execute(Path(a.run_dir), a.run_id, timeout=a.timeout)


if __name__ == "__main__":
    main()
