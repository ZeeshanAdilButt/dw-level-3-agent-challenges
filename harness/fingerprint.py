"""Fingerprints and the run manifest (decision B1).

Provenance is not eligibility: the manifest records what a run executed; `comparable` (diff.py) decides what may
be compared.
"""
import json
import os
import urllib.request
from pathlib import Path

from . import paths
from .graders import GRADER_VERSION
from .util import git, sha

CODE_DIRS = ("app", "harness", "mock_api")


def _files(base: Path, pattern="*"):
    return sorted(p for p in base.rglob(pattern) if p.is_file() and "__pycache__" not in p.parts) if base.exists() else []


def tree_hash_of(root: Path, dirs, suffixes=(".py", ".toml", ".md", ".yaml", ".yml", ".json", ".txt")) -> str:
    h = []
    for d in dirs:
        for p in _files(root / d):
            if p.suffix in suffixes:
                h.append(f"{p.relative_to(root).as_posix()}:{sha(p.read_bytes())}")
    return sha("\n".join(h))


def code_fingerprint(root: Path = None) -> dict:
    root = root or paths.root()
    return {"commit": git("rev-parse", "HEAD", cwd=root), "tree": git("rev-parse", "HEAD^{tree}", cwd=root),
            "content_hash": tree_hash_of(root, CODE_DIRS)[:16]}


def corpus_fingerprint(pack_dir) -> str:
    h = [f"{p.name}:{sha(p.read_bytes())}" for p in _files(Path(pack_dir) / "corpus", "*.md")]
    return sha("\n".join(h))[:16]


def prompts_fingerprint(root: Path = None) -> str:
    root = root or paths.root()
    return tree_hash_of(root, ("app/prompts", "app/rules"))[:16]


def fixtures_fingerprint(pack_dir) -> str:
    f = Path(pack_dir) / "tools" / "fixture.json"
    return sha(f.read_bytes())[:16] if f.exists() else "none"


def ollama_digest(model: str):
    """The digest Ollama reports for a local model, or None when Ollama is not reachable or lacks the model."""
    if os.environ.get("DW_NO_DIGEST"):
        return None
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")      # 127.0.0.1: "localhost" can stall on Windows
    try:
        data = json.load(urllib.request.urlopen(f"{url}/api/tags", timeout=3))
    except Exception:
        return None
    for m in data.get("models", []):
        if m.get("name") in (model, f"{model}:latest"):
            return m.get("digest")
    return None


def prediction_commit(root: Path = None) -> dict:
    """The last commit that touched predictions/, with its commit time, or None values if there is none."""
    root = root or paths.root()
    out = git("log", "-1", "--format=%H|%cI", "--", "predictions", cwd=root)
    if not out:
        return {"commit": None, "committed_at": None}
    c, at = out.split("|", 1)
    return {"commit": c, "committed_at": at}


def build_manifest(settings: dict, pack_dir, root: Path = None, embed_digest: bool = True, model_digest: bool = True) -> dict:
    from .cases import qset_version
    root = root or paths.root()
    local = settings.get("model_path") == "local"
    m = {
        "code": code_fingerprint(root),
        "prompts": prompts_fingerprint(root),
        "corpus_hash": corpus_fingerprint(pack_dir),
        "index_settings": {k: settings.get(k) for k in ("chunker", "chunk_size", "overlap", "retriever", "embed_model")},
        "embed_model_digest": ollama_digest(settings.get("embed_model", "")) if embed_digest else None,
        "model": {"path": settings.get("model_path"),
                  "name": settings.get("hosted_model") if settings.get("model_path") == "hosted" else settings.get("model"),
                  "digest": ollama_digest(settings.get("model", "")) if (model_digest and local) else None},
        "tool_fixtures": fixtures_fingerprint(pack_dir),
        "grader_version": GRADER_VERSION,
        "question_set_version": qset_version(pack_dir),
    }
    m["fingerprint"] = sha(m)[:16]
    return m
