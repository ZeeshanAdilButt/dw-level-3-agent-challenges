"""The harness's one door to retrieval.

`Agent.retrieve(query, principal)` from app/core.py is the real path (it applies the access checks, context
expansion and the token budget). Until app/core.py exists, this adapter calls app/retrieval directly with no
expansion and the same global token budget, so the screen works either way. `path` says which one ran.
"""
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.retrieval.chunkers import chunk_corpus
from app.retrieval.corpus import TOKEN, count_tokens, load_corpus

from . import paths
from .canonical import canonical_text


@dataclass
class Retrieved:
    ranked_ids: list
    expanded_ids: list = field(default_factory=list)
    delivered_ids: list = field(default_factory=list)
    delivered_text: str = ""
    delivered_tokens: int = 0
    truncated: bool = False


def _cid(x) -> str:
    if isinstance(x, tuple):
        x = x[0]
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get("chunk_id") or x.get("id")
    return x.chunk_id


def make_retriever(name, chunks):
    from .screen import make_retriever as mk
    return mk(name, chunks)


def locate(body: str, text: str, cursor: int = 0):
    """Offsets of a chunk's text inside the document's canonical text, or None if it cannot be placed."""
    i = body.find(text, cursor)
    if i < 0:
        i = body.find(text)
    if i < 0 and "\n" in text:  # a heading chunk starts with an added heading line
        rest = text.split("\n", 1)[1]
        j = body.find(rest)
        if j >= 0:
            return j, j + len(rest)
    if i < 0:
        probe = text[:40]
        j = body.find(probe) if probe else -1
        return (j, min(len(body), j + len(text))) if j >= 0 else None
    return i, i + len(text)


def canonical_shift(pack_dir, docs: dict) -> dict:
    """Where each loaded body (stripped) starts inside the document's canonical text."""
    out = {}
    for did, d in docs.items():
        f = Path(pack_dir) / "corpus" / f"{did}.md"
        canon = canonical_text(f.read_text(encoding="utf-8")) if f.exists() else d.body
        out[did] = max(0, canon.find(d.body))
    return out


def chunk_table(docs: dict, chunks, pack_dir=None) -> dict:
    """{chunk_id: [doc_id, start, end]} in canonical text offsets (end exclusive). Unplaceable chunks are left out."""
    out, cursor = {}, {}
    shift = canonical_shift(pack_dir, docs) if pack_dir else {}
    for c in chunks:
        body = docs[c.doc_id].body
        span = locate(body, c.text, cursor.get(c.doc_id, 0))
        if span:
            d = shift.get(c.doc_id, 0)
            out[c.chunk_id] = [c.doc_id, span[0] + d, span[1] + d]
            cursor[c.doc_id] = span[0] + 1
    return out


def section_table(docs: dict, pack_dir=None) -> dict:
    """{"<doc>#sec<k>": [doc_id, start, end]} for the section parents context expansion delivers (the same numbering as
    app/context.py: a text before the first heading is section 0 when it is not empty)."""
    from app.retrieval.chunkers import HEADING
    out = {}
    shift = canonical_shift(pack_dir, docs) if pack_dir else {}
    for did, d in docs.items():
        body, marks = d.body, list(HEADING.finditer(d.body))
        bounds = [(0, len(body))] if not marks else (([(0, marks[0].start())] if body[:marks[0].start()].strip() else [])
                                                      + [(m.start(), marks[i + 1].start() if i + 1 < len(marks) else len(body))
                                                         for i, m in enumerate(marks)])
        for k, (s, e) in enumerate(bounds):
            piece = body[s:e]
            start = s + len(piece) - len(piece.lstrip())
            out[f"{did}#sec{k}"] = [did, start + shift.get(did, 0), start + len(piece.strip()) + shift.get(did, 0)]
    return out


def _truncate(text: str, tokens: int, limit: int) -> str:
    spans = [m.span() for m in TOKEN.finditer(text)]
    return text[:spans[limit - 1][1]] if limit > 0 and spans and limit < len(spans) else text


class RetrievalBridge:
    def __init__(self, settings: dict, pack_dir=None):
        self.settings = settings
        self.pack_dir = Path(pack_dir or paths.pack_dir(settings["pack"]))
        self.docs = load_corpus(self.pack_dir)
        self.agent = None
        self.path = "modules"
        try:
            from app.core import Agent  # type: ignore
            if hasattr(Agent, "retrieve"):
                from .worker import make_mock
                self.agent = Agent(settings, self.pack_dir, make_mock(self.pack_dir, "screen"))  # the core's toolbox wants a mock
                self.path = "agent"
        except Exception as e:  # the core is being written in parallel; fall back and say so
            self.agent_error = f"{type(e).__name__}: {e}"
        self.chunks = chunk_corpus(self.docs, settings["chunker"], settings["chunk_size"], settings["overlap"])
        self.by_id = {c.chunk_id: c for c in self.chunks}
        self.table = {**section_table(self.docs, self.pack_dir), **chunk_table(self.docs, self.chunks, self.pack_dir)}
        self.index_seconds = 0.0
        self._retriever = None
        if self.agent is None:
            t = time.time()
            self._retriever = make_retriever(settings["retriever"], self.chunks)
            self.index_seconds = time.time() - t

    def retrieve(self, query: str, principal=None) -> Retrieved:
        if self.agent is not None:
            r = self.agent.retrieve(query, principal)
            ranked = [_cid(x) for x in r.ranked]
            return Retrieved(ranked, [_cid(x) for x in r.expanded], [_cid(x) for x in r.delivered],
                             r.delivered_text, r.delivered_tokens, bool(r.truncated))
        hits = self._retriever.search(query, self.settings["top_k"])
        limit = self.settings["context_token_limit"]
        parts, ids, used, truncated = [], [], 0, False
        for chunk, _ in hits:
            if used >= limit:
                truncated = True
                break
            text = chunk.text
            if used + chunk.tokens > limit:
                text, truncated = _truncate(text, chunk.tokens, limit - used), True
            parts.append(text)
            ids.append(chunk.chunk_id)
            used += min(chunk.tokens, limit - used)
        return Retrieved([c.chunk_id for c, _ in hits], [], ids, "\n\n".join(parts), used, truncated)


def install_embedding_stats(embed_model: str, uncached_queries: bool) -> dict:
    """Wrap app.retrieval.vectors.embed to count lookups and cache-miss calls; optionally never cache queries.

    Full runs use uncached queries so a new customer's query cost is in the latency; screens use the cache and say
    so in the record. Returns a stats dict that fills as embeddings are requested."""
    stats = {"lookups": 0, "cache_misses": 0, "network_calls": 0, "queries_cached": not uncached_queries}
    try:
        import app.retrieval.vectors as V
    except Exception:
        return stats
    V.MODEL = embed_model or V.MODEL
    orig = V.embed

    def wrapped(texts, prefix, model=None):
        stats["lookups"] += len(texts)
        if uncached_queries and prefix.startswith("search_query"):
            out = []
            for i in range(0, len(texts), 32):
                out += V._embed_batch([prefix + t for t in texts[i:i + 32]], model)
            stats["cache_misses"] += len(texts)
            stats["network_calls"] += len(texts)
            return out
        missing = sum(1 for t in texts if not (V.CACHE / (V._key(prefix, t, model) + ".json")).exists())
        stats["cache_misses"] += missing
        stats["network_calls"] += missing
        return orig(texts, prefix, model)

    V.embed = wrapped
    return stats


def offsets_table(settings: dict, pack_dir=None):
    """(docs, {chunk_id: [doc, start, end]}) for the settings' chunker and every section parent, with no retriever or agent built."""
    pd = Path(pack_dir or paths.pack_dir(settings["pack"]))
    docs = load_corpus(pd)
    chunks = chunk_corpus(docs, settings["chunker"], settings["chunk_size"], settings["overlap"])
    return docs, {**section_table(docs, pd), **chunk_table(docs, chunks, pd)}
