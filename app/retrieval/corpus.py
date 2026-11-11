"""Load a pack's corpus: Markdown files with YAML front matter."""
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TOKEN = re.compile(r"\w+|[^\w\s]")


def count_tokens(text: str) -> int:
    """Word-and-punctuation count. It approximates model tokens; the chapters say so."""
    return len(TOKEN.findall(text))


@dataclass
class Document:
    doc_id: str
    title: str
    meta: dict
    body: str
    links: list = field(default_factory=list)


def load_corpus(pack_dir) -> dict:
    docs = {}
    for path in sorted((Path(pack_dir) / "corpus").glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        _, front, body = raw.split("---", 2)
        meta = yaml.safe_load(front)
        docs[meta["doc_id"]] = Document(meta["doc_id"], meta["title"], meta, body.strip(), meta.get("links") or [])
    return docs
