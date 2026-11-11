"""The mock company API. One MockClient per namespace holds that namespace's state; `reset()` returns it to the fixture.

Every call takes the principal from the core (never from the model's arguments) and an idempotency key. A repeated key
returns the stored receipt and changes nothing. The company rules the tools enforce live in `mock_api/rules.py`.
"""
from __future__ import annotations

import copy
import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import asdict, is_dataclass
from pathlib import Path

from . import rules


def _principal_dict(p) -> dict:
    return asdict(p) if is_dataclass(p) else dict(p)


class MockClient:
    """In-process mock. `pack_dir` is a pack folder (packs/quillon); `namespace` keeps cases apart."""

    def __init__(self, pack_dir: Path, namespace: str = "default"):
        self.pack_dir = Path(pack_dir)
        self.namespace = namespace
        name = self.pack_dir.name
        for suffix in ("-mine", "-practice"):       # a learner's own copy of a company's pack keeps the company's rules
            if name.endswith(suffix) and name[: -len(suffix)] in ("quillon", "juniper", "saltmarsh"):
                name = name[: -len(suffix)]
        self.pack = name
        self._fixture = json.loads((self.pack_dir / "tools" / "fixture.json").read_text(encoding="utf-8"))
        self._lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._data = rules.new_state(self.pack, copy.deepcopy(self._fixture), self.namespace)

    def call(self, name: str, args: dict, principal, idempotency_key: str) -> dict:
        """A receipt: {"ok", "receipt_id", "tool", "result" or "error", "idempotency_key", "replayed"}."""
        p = _principal_dict(principal)
        with self._lock:
            d = self._data
            stored = d["_idem"].get(idempotency_key)
            if stored is not None:
                if stored["tool"] != name or stored["principal_id"] != p["id"]:
                    return {"ok": False, "tool": name, "error": "idempotency_key_reused", "receipt_id": None,
                            "idempotency_key": idempotency_key, "replayed": False}
                out = copy.deepcopy(stored["receipt"])
                out["replayed"] = True
                return out
            d["_seq"] += 1
            receipt = {"receipt_id": f"rcpt-{self.namespace}-{d['_seq']}", "tool": name, "idempotency_key": idempotency_key, "replayed": False}
            try:
                handler = rules.HANDLERS[self.pack][name]
            except KeyError:
                receipt.update(ok=False, error="unknown_tool")
            else:
                receipt.update(handler(d, dict(args or {}), p))
            receipt.setdefault("ok", False)
            receipt.setdefault("result", {})
            receipt["status"] = "ok" if receipt["ok"] else str(receipt.get("error") or "error")
            if not receipt["ok"]:
                receipt["error"] = str(receipt.get("error") or "error")
            d["receipts"].append({"receipt_id": receipt["receipt_id"], "tool": name, "principal_id": p["id"], "ok": receipt["ok"],
                                  "args": dict(args or {}), "error": receipt.get("error"), "idempotency_key": idempotency_key})
            d["_idem"][idempotency_key] = {"tool": name, "principal_id": p["id"], "receipt": copy.deepcopy(receipt)}
            return copy.deepcopy(receipt)

    def state(self) -> dict:
        with self._lock:
            return rules.public_state(self._data)


class HttpMockClient:
    """The same methods over HTTP, for the examiner's hosted mock (`MOCK_API_URL`)."""

    def __init__(self, base_url: str, namespace: str, pack: str | None = None, timeout: float = 120.0):
        self.base = base_url.rstrip("/")
        self.namespace = namespace
        self.pack = pack or os.environ.get("DW_PACK")
        self.timeout = timeout

    def _req(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.pack:
            headers["X-DW-Pack"] = self.pack
        token = os.environ.get("X_EXAM_TOKEN") or os.environ.get("DW_EXAM_TOKEN")
        if token:
            headers["X-Exam-Token"] = token
        req = urllib.request.Request(f"{self.base}/ns/{self.namespace}{path}", data, headers, method=method)
        try:
            return json.load(urllib.request.urlopen(req, timeout=self.timeout))
        except urllib.error.HTTPError as e:
            return {"ok": False, "error": f"http_{e.code}", "receipt_id": None}
        except (urllib.error.URLError, OSError) as e:
            return {"ok": False, "error": f"mock_unreachable: {e}", "receipt_id": None}

    def call(self, name: str, args: dict, principal, idempotency_key: str) -> dict:
        return self._req("POST", f"/tools/{name}", {"args": args, "principal": _principal_dict(principal),
                                                    "idempotency_key": idempotency_key})

    def state(self) -> dict:
        return self._req("GET", "/state")

    def reset(self) -> None:
        self._req("POST", "/reset", {})
