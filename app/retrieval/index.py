"""The index an Agent searches: the pack's corpus cut into chunks, plus the retriever the settings name.

Built once per (pack, chunker, size, overlap, retriever) and cached, so a run of 148 cases cuts and indexes once.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from .bm25 import BM25
from .chunkers import Chunk, chunk_corpus
from .corpus import load_corpus
from .fusion import Hybrid
from .trigram import Trigram

_CACHE: dict = {}
_LOCK = threading.Lock()


class SharedBM25(BM25):
    """The shipped BM25 over a connection other threads may use (the adapter serves requests from a thread pool)."""

    def __init__(self, chunks):
        self.chunks = chunks
        self._lock = threading.Lock()
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.execute("CREATE VIRTUAL TABLE c USING fts5(text, tokenize = \"porter unicode61\")")
        self.db.executemany("INSERT INTO c(rowid, text) VALUES (?, ?)", [(i, ch.text) for i, ch in enumerate(chunks)])

    def search(self, query, k=5):
        with self._lock:
            return super().search(query, k)


def _str(v):
    return None if v is None else str(v)


class Index:
    def __init__(self, pack_dir: Path, settings: dict):
        self.pack_dir = Path(pack_dir)
        self.docs = load_corpus(self.pack_dir)
        for d in self.docs.values():                       # YAML may turn bare dates into date objects
            for k in ("effective_from", "effective_to"):
                if k in d.meta:
                    d.meta[k] = _str(d.meta[k])
            ap = d.meta.get("applies_to")
            if isinstance(ap, dict):
                ap["from"], ap["to"] = _str(ap.get("from")), _str(ap.get("to"))
        self.chunks = chunk_corpus(self.docs, settings["chunker"], settings["chunk_size"], settings["overlap"])
        self.by_id: dict[str, Chunk] = {c.chunk_id: c for c in self.chunks}
        self.by_doc: dict[str, list[Chunk]] = {}
        for c in self.chunks:
            self.by_doc.setdefault(c.doc_id, []).append(c)
        for lst in self.by_doc.values():
            lst.sort(key=lambda c: c.position)
        self.bm25 = SharedBM25(self.chunks)                      # always built: the leak check searches it without any access filter
        self.embed_model = settings.get("embed_model")
        self.retriever = self._make(settings["retriever"])
        self.titles = {i: d.title for i, d in self.docs.items()}

    def _make(self, name: str):
        if name == "bm25":
            return self.bm25
        if name == "trigram":
            return Trigram(self.chunks)
        from .vectors import Vectors
        if name == "vector":
            return Vectors(self.chunks, self.embed_model)
        if name == "hybrid":
            return Hybrid(self.bm25, Vectors(self.chunks, self.embed_model))
        raise ValueError(f"unknown retriever {name}")

    def search(self, query: str, k: int):
        return self.retriever.search(query, k)

    def search_unfiltered(self, query: str, k: int = 5):
        """BM25 over every chunk, public and internal. Used only by the leak check."""
        return self.bm25.search(query, k)

    def meta(self, doc_id: str) -> dict:
        return self.docs[doc_id].meta


def get_index(pack_dir: Path, settings: dict) -> Index:
    key = (str(Path(pack_dir).resolve()), settings["chunker"], settings["chunk_size"], settings["overlap"], settings["retriever"],
           settings["embed_model"])
    with _LOCK:
        if key not in _CACHE:
            _CACHE[key] = Index(pack_dir, settings)
        return _CACHE[key]
