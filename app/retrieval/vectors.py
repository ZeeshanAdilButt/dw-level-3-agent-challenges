"""Embeddings from a local Ollama model, cached on disk, searched by cosine similarity in memory."""
import hashlib
import json
import math
import os
import urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("DW_CACHE", ".cache")) / "embeddings"
URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")


def _key(prefix, text, model=None):
    return hashlib.sha256(f"{model or MODEL}|{prefix}|{text}".encode()).hexdigest()


def _embed_batch(texts, model=None):
    body = json.dumps({"model": model or MODEL, "input": texts, "truncate": True}).encode()
    req = urllib.request.Request(f"{URL}/api/embed", body, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))["embeddings"]


def embed(texts, prefix, model=None):
    """Embeddings for texts with one prefix, from the cache or the model (`model`, else EMBED_MODEL)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out, todo = [None] * len(texts), []
    for i, t in enumerate(texts):
        f = CACHE / (_key(prefix, t, model) + ".json")
        if f.exists():
            out[i] = json.loads(f.read_text())
        else:
            todo.append(i)
    for start in range(0, len(todo), 32):
        idx = todo[start:start + 32]
        for i, v in zip(idx, _embed_batch([prefix + texts[i] for i in idx], model)):
            out[i] = v
            (CACHE / (_key(prefix, texts[i], model) + ".json")).write_text(json.dumps(v))
    return out


def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class Vectors:
    def __init__(self, chunks, model=None):
        self.chunks = chunks
        self.model = model                     # the settings' embed_model; None means EMBED_MODEL
        self.vecs = [_norm(v) for v in self._embed([c.text for c in chunks], "search_document: ")]

    def _embed(self, texts, prefix):
        return embed(texts, prefix, model=self.model) if self.model else embed(texts, prefix)

    def search(self, query, k=5):
        q = _norm(self._embed([query], "search_query: ")[0])
        scored = sorted(((sum(a * b for a, b in zip(q, v)), c) for c, v in zip(self.chunks, self.vecs)),
                        key=lambda t: (-t[0], t[1].chunk_id))
        return [(c, s) for s, c in scored[:k]]
