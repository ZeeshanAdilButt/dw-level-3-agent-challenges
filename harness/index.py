"""python -m harness index: build the vector index for the pack under the resolved chunk settings.

    python -m harness index --pack <your-pack> [--set chunker=heading] [--check-truncation]

Embeddings are cached on disk, so the index is built once per chunk text. `--check-truncation` embeds every chunk
on its own with truncation off and reads the embedding model's own token count from Ollama (`prompt_eval_count`),
so "400-token chunks" is checked against the model's tokenizer, not against the word-and-punctuation count the
chunkers use. A chunk the model would cut is listed: the cut text is absent from that chunk's embedding.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

from . import config, paths
from .retrieval_bridge import install_embedding_stats
from .retrieval_bridge import RetrievalBridge

PREFIX = "search_document: "


def _post(path, body, timeout=300):
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    req = urllib.request.Request(url + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def context_length(model: str):
    try:
        info = _post("/api/show", {"model": model}, 30).get("model_info", {})
    except Exception:
        return None
    return next((v for k, v in info.items() if k.endswith(".context_length")), None)


def token_count(model: str, text: str) -> tuple:
    """(tokens, truncated). With truncation off, Ollama refuses an input longer than the model's context."""
    try:
        r = _post("/api/embed", {"model": model, "input": PREFIX + text, "truncate": False})
        return r.get("prompt_eval_count"), False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace").lower()
        if "context" in body or "length" in body or e.code == 400:
            return None, True
        raise


def check_truncation(settings: dict, chunks: list) -> dict:
    model = settings["embed_model"]
    ctx = context_length(model)
    counts, cut = {}, []
    for c in chunks:
        n, truncated = token_count(model, c.text)
        counts[c.chunk_id] = n
        if truncated or (n is not None and ctx and n > ctx):
            cut.append(c.chunk_id)
    known = [n for n in counts.values() if n is not None]
    return {"embed_model": model, "context_length": ctx, "chunks": len(chunks), "max_model_tokens": max(known) if known else None,
            "mean_model_tokens": round(sum(known) / len(known), 1) if known else None,
            "max_chunker_tokens": max(c.tokens for c in chunks) if chunks else 0, "would_be_cut": cut}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness index")
    ap.add_argument("--pack", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="key=value")
    ap.add_argument("--parent")
    ap.add_argument("--check-truncation", action="store_true")
    a = ap.parse_args(argv)
    try:
        settings, _, change = config.resolve(pack=a.pack, parent=a.parent, sets=config.parse_sets(a.set))
    except config.SettingsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(config.describe(settings, change))
    stats = install_embedding_stats(settings["embed_model"], uncached_queries=False)
    t = time.time()
    try:
        s2 = dict(settings, retriever="vector")
        bridge = RetrievalBridge(s2, paths.pack_dir(settings["pack"]))
        bridge.retrieve("index warm-up")  # with the core's agent the index may build on first use
    except (urllib.error.URLError, OSError, ConnectionError) as e:
        print(f"error: cannot reach the embedding model ({e}). Is Ollama running with {settings['embed_model']} pulled?", file=sys.stderr)
        return 2
    secs = time.time() - t
    print(f"\nindex ready: {len(bridge.chunks)} chunks, {secs:.1f} s (cache misses {stats['cache_misses']} of {stats['lookups']} lookups; "
          f"a rerun is near instant)")
    if a.check_truncation:
        try:
            rep = check_truncation(settings, bridge.chunks)
        except (urllib.error.URLError, OSError) as e:
            print(f"error: cannot count tokens with the embedding model ({e})", file=sys.stderr)
            return 2
        print(f"truncation check with {rep['embed_model']} (context length {rep['context_length']}): "
              f"largest chunk is {rep['max_model_tokens']} model tokens ({rep['max_chunker_tokens']} by the chunkers' count), "
              f"mean {rep['mean_model_tokens']}")
        if rep["would_be_cut"]:
            print(f"  {len(rep['would_be_cut'])} chunk(s) would be cut: {', '.join(rep['would_be_cut'][:10])}")
            return 1
        print("  no chunk would be cut")
    return 0
