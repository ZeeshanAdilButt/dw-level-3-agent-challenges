"""One Chat Completions client for Ollama or a hosted model, plus a deterministic stub that never touches the network.

`model_path`: local (Ollama's OpenAI-compatible endpoint), hosted (DW_HOSTED_BASE_URL + DW_HOSTED_API_KEY), stub (tests, CI).
Every call opens a `model` span, records tokens and latency, and uses a seed made from the request id, the call number
and, in a harness run, the run's seed salt (DW_SEED_SALT).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import tomllib
from functools import lru_cache
from pathlib import Path

from .prompts import parse_documents
from .retrieval.corpus import count_tokens
from .rules.common import POLICY_NUMBER, parse_dates, parse_quote_request


class ModelError(RuntimeError):
    pass


@dataclass
class ChatResult:
    text: str
    tool_calls: list = field(default_factory=list)   # [{"id", "name", "arguments": dict}]
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    model: str = ""


SEED_SALT_ENV = "DW_SEED_SALT"
_NO_TEMPERATURE: dict = {}      # endpoint + model pairs that refused `temperature`


def _seed(request_id: str, call_no: int, salt: str = "") -> int:
    """The seed for one model call. The harness sets a salt per run (the run id), so repeated runs of the same
    cases sample independently while a replay of the same run id gets the same seeds."""
    key = f"{salt}:{request_id}:{call_no}" if salt else f"{request_id}:{call_no}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % (2 ** 31)


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


class ModelClient:
    def __init__(self, settings: dict):
        self.settings = settings
        self.path = "stub" if os.environ.get("DW_MODEL_PATH") == "stub" else settings["model_path"]

    @property
    def model_name(self) -> str:
        if self.path == "stub":
            return "stub"
        return self.settings["hosted_model"] if self.path == "hosted" else self.settings["model"]

    def chat(self, messages: list[dict], tools: list[dict] | None, span_name: str, tracer) -> ChatResult:
        with tracer.span("model", step=span_name) as sp:
            started = time.perf_counter()
            call_no = tracer.next_call()
            if self.path == "stub":
                res = self._stub(messages, tools, span_name)
            else:
                res = self._http(messages, tools, _seed(tracer.request_id, call_no, os.environ.get(SEED_SALT_ENV, "")))
            res.latency_ms = (time.perf_counter() - started) * 1000.0
            sp.model, sp.tokens_in, sp.tokens_out = res.model, res.tokens_in, res.tokens_out
        return res

    # ---- real endpoints -------------------------------------------------------------------------------------------
    def _http(self, messages, tools, seed) -> ChatResult:
        if self.path == "hosted":
            base = os.environ.get("DW_HOSTED_BASE_URL", "").rstrip("/")
            key = os.environ.get("DW_HOSTED_API_KEY", "")
            if not base or not key:
                raise ModelError("hosted path needs DW_HOSTED_BASE_URL and DW_HOSTED_API_KEY")
            url, headers = base + "/chat/completions", {"Authorization": f"Bearer {key}"}
        else:
            url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/v1/chat/completions"
            headers = {}
        body = {"model": self.model_name, "messages": messages, "seed": seed, "stream": False}
        if not _NO_TEMPERATURE.get(url + self.model_name):
            body["temperature"] = self.settings["temperature"]
        if tools:
            body["tools"] = tools
        data = self._post(url, headers, body)
        msg = data["choices"][0]["message"]
        return self._parse(data, msg)

    def _post(self, url, headers, body) -> dict:
        """POST once; a model that refuses `temperature` (some hosted models do) is asked again without it, and remembered."""
        req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
        try:
            return json.load(urllib.request.urlopen(req, timeout=300))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code == 400 and "temperature" in detail and "temperature" in body:
                _NO_TEMPERATURE[url + body["model"]] = True
                return self._post(url, headers, {k: v for k, v in body.items() if k != "temperature"})
            raise ModelError(f"model call failed: HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ModelError(f"model call failed: {e}") from e

    def _parse(self, data, msg) -> ChatResult:
        msg = data["choices"][0]["message"]
        calls = []
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc.get("function", {})
            raw = fn.get("arguments", {})
            try:
                args = json.loads(raw) if isinstance(raw, str) else dict(raw)
            except (ValueError, TypeError):
                args = {"_invalid": str(raw)}
            if not isinstance(args, dict):
                args = {"_invalid": str(raw)}
            calls.append({"id": tc.get("id") or f"call-{i}", "name": fn.get("name", ""), "arguments": args})
        usage = data.get("usage") or {}
        return ChatResult(text=_strip_think(msg.get("content") or ""), tool_calls=calls,
                          tokens_in=int(usage.get("prompt_tokens", 0)), tokens_out=int(usage.get("completion_tokens", 0)),
                          model=data.get("model") or self.model_name)

    # ---- the deterministic stub -----------------------------------------------------------------------------------
    def _stub(self, messages, tools, span_name) -> ChatResult:
        text, calls = stub_reply(messages, tools, span_name)
        tin = sum(count_tokens(str(m.get("content") or "")) for m in messages)
        return ChatResult(text=text, tool_calls=calls, tokens_in=tin, tokens_out=count_tokens(text), model="stub")


# ---- prices: config/prices.toml (dated). Tokens and dollars stay separate; each call is priced at its own model's rates ----
PRICES_PATH = Path(__file__).resolve().parents[1] / "config" / "prices.toml"
_FALLBACK = {"input": 0.0, "output": 0.0, "hosted_equivalent_input": 0.10, "hosted_equivalent_output": 0.40}


@lru_cache(maxsize=1)
def price_table() -> dict:
    return tomllib.loads(PRICES_PATH.read_text(encoding="utf-8")) if PRICES_PATH.exists() else {"date": "unknown", "models": {}}


def cost(model: str, tokens_in: int, tokens_out: int) -> tuple[float, float]:
    """(price paid, hosted-equivalent price) in USD for one call. A local model pays 0."""
    models = price_table().get("models", {})
    r = models.get(model) or models.get("default-hosted") or _FALLBACK
    return ((tokens_in * r["input"] + tokens_out * r["output"]) / 1e6,
            (tokens_in * r["hosted_equivalent_input"] + tokens_out * r["hosted_equivalent_output"]) / 1e6)


# ---- the stub: deterministic, offline, just smart enough to exercise the core ----------------------------------------
_CLASSIFY = [
    ("red_flag", re.compile(r"chest.{0,40}(funny|tight|heavy|pressure|pain|hurt|squeez)|(arm|hand).{0,30}(numb|dead|heavy|tingl)|can'?t breathe|"
                            r"face.{0,20}droop|slurr|want to (die|end it)|kill myself|end(ing)? it all|bleeding.{0,20}(won'?t|heavily)|throat.{0,15}(clos|swell)", re.I)),
    ("medicine_advice", re.compile(r"\b(dose|tablets?|pills?|medicine|medication)\b.{0,40}\b(stop|start|double|increase|skip|take)\b|\b(stop|start|double|skip|take)\b.{0,30}\b(tablets?|pills?|medicine|medication)\b|lose weight", re.I)),
    ("diagnosis_request", re.compile(r"what do i have|what.s wrong with me|is it (cancer|a )", re.I)),
]


def _question(text: str) -> str:
    """The question (single agent) or the router's note (a specialist): the last labelled line of the user message."""
    return re.split(r"Question:|Note from the router:", text)[-1].strip()


def stub_reply(messages: list, tools: list | None, step: str):
    """(text, tool_calls) for the stub model. `step` is the span name the core gave the call."""
    user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    system = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
    q = _question(user)
    if step == "classifier":
        cat = next((c for c, rx in _CLASSIFY if rx.search(q)), "none")
        return json.dumps({"category": cat}), []
    if step == "router":
        areas = re.findall(r"^- ([\w-]+): (.*)$", system, re.M)
        words = set(re.findall(r"\w+", q.lower()))
        scored = sorted(((len(words & set(re.findall(r"\w+", desc.lower()))), -i, name) for i, (name, desc) in enumerate(areas)), reverse=True)
        picks = [scored[0][2]] if scored else []
        if len(scored) > 1 and scored[1][0] > 0 and scored[1][0] == scored[0][0] and "and" in words:
            picks.append(scored[1][2])
        return json.dumps([{"area": a, "note": f"Answer from your documents: {q}"} for a in picks]), []   # the stub's note carries the question
    if step == "reviewer":
        draft = user.split("DRAFT:", 1)[-1].split("CITED:", 1)[0]
        ok = "[doc-" in draft or "I do not have that" in draft or "ASK:" in draft or "REVISED" in user
        return json.dumps({"verdict": "pass"} if ok else {"verdict": "revise", "feedback": "Cite the document id you used."}), []
    if step.startswith("merge"):
        return " ".join(re.findall(r"PART \d:\s*(.*?)(?=\nPART \d:|\Z)", user, re.S)).strip(), []
    low = q.lower()
    tool_msgs = [m for m in messages if m["role"] == "tool"]
    if tool_msgs:
        return "Done. " + str(tool_msgs[-1]["content"])[:300], []
    if tools:
        names = {t["function"]["name"] for t in tools}
        if "lookup_account" in names and re.search(r"\b(my account|my renewal|renewal date|how many seats|my plan)\b", low):
            return "", [{"id": "stub-1", "name": "lookup_account", "arguments": {}}]
        if "create_quote" in names and re.search(r"\bquote\b", low):
            qr = parse_quote_request(q)
            if {"plan", "seats", "term"} <= qr.keys():
                return "", [{"id": "stub-1", "name": "create_quote", "arguments": qr}]
        if "lookup_policy" in names and POLICY_NUMBER.search(q) and parse_dates(q):
            return "", [{"id": "stub-1", "name": "lookup_policy",
                         "arguments": {"policy_number": POLICY_NUMBER.search(q).group(0), "date_of_birth": parse_dates(q)[-1]}}]
    docs = parse_documents(user)
    if not docs:
        return "I do not have that. A person can help with this question.", []
    doc_id, body = docs[0]
    lines = [ln for ln in body.splitlines() if ln.strip() and not ln.startswith("#")]
    snippet = " ".join(" ".join(lines).split()[:35])
    return f"{snippet} [{doc_id}]", []
