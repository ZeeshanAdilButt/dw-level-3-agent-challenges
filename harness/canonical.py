"""The canonical text of a document (facts/SCHEMA.md): the body after the front matter, LF line endings, no leading
blank lines. Gold-span offsets and doc_sha256 are defined on it, whatever a learner's chunker does."""
import hashlib

FM_END = "\n---\n"


def canonical_text(raw: str) -> str:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    if raw.startswith("---\n"):
        end = raw.find(FM_END, 3)
        if end != -1:
            raw = raw[end + len(FM_END):]
    return raw.lstrip("\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
