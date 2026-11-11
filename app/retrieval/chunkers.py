"""Three ways to cut a document. Each chunk keeps its document id, heading and position."""
import re
from dataclasses import dataclass

from .corpus import TOKEN, count_tokens

HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    heading: str
    text: str
    tokens: int
    position: int  # order inside the document, used for neighbours


def _split_tokens(text, size, overlap):
    """Cut text into windows of `size` tokens that share `overlap` tokens, keeping the original spacing."""
    spans = [m.span() for m in TOKEN.finditer(text)]
    if not spans:
        return []
    step = max(1, size - overlap)
    pieces, start = [], 0
    while start < len(spans):
        end = min(start + size, len(spans))
        pieces.append(text[spans[start][0]:spans[end - 1][1]])
        if end == len(spans):
            break
        start += step
    return pieces


def check_overlap(size, overlap):
    if not 0 <= overlap < size:
        raise ValueError(f"overlap must satisfy 0 <= overlap < size (got overlap={overlap}, size={size})")


def _fixed_chunks(doc, size, overlap):
    return [Chunk(f"{doc.doc_id}#{i}", doc.doc_id, doc.title, t, count_tokens(t), i)
            for i, t in enumerate(_split_tokens(doc.body, size, overlap))]


def chunk_with_overlap(doc, size=400, overlap=0):
    """Starter: overlap 0 only, so the baseline cut works. Write the overlap."""
    check_overlap(size, overlap)
    if overlap:
        raise NotImplementedError("YOUR TURN: write chunk_with_overlap")
    return _fixed_chunks(doc, size, 0)


def fixed(doc, size=400, overlap=0):
    return chunk_with_overlap(doc, size, overlap)


def sections(doc):
    """Split on Markdown headings; each section carries its heading."""
    marks = list(HEADING.finditer(doc.body))
    if not marks:
        return [(doc.title, doc.body)]
    out = []
    if doc.body[:marks[0].start()].strip():
        out.append((doc.title, doc.body[:marks[0].start()]))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(doc.body)
        out.append((m.group(2).strip(), doc.body[m.start():end]))
    return out


def by_heading(doc, max_size=400):
    raise NotImplementedError("YOUR TURN: write chunk_by_heading")


chunk_by_heading = by_heading        # the names the chapter uses


def chunk_corpus(docs, method="fixed", size=400, overlap=0):
    out = []
    for doc in docs.values():
        if method == "fixed":
            out += fixed(doc, size, overlap)
        elif method == "heading":
            out += by_heading(doc, size)
        else:
            raise ValueError(f"unknown chunker {method}")
    return out
