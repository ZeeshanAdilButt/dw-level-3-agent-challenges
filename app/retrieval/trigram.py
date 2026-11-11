"""Trigram similarity: lowercase, NFKC, each word padded with two spaces before and one after
(as pg_trgm does), character trigrams, Jaccard over the two sets, top k by score."""
import unicodedata


def trigrams(text):
    text = unicodedata.normalize("NFKC", text).lower()
    grams = set()
    for word in "".join(ch if ch.isalnum() else " " for ch in text).split():
        w = "  " + word + " "
        grams.update(w[i:i + 3] for i in range(len(w) - 2))
    return grams


def jaccard(a, b):
    union = a | b
    return len(a & b) / len(union) if union else 0.0


class Trigram:
    def __init__(self, chunks):
        self.chunks = chunks
        self.sets = [trigrams(c.text) for c in chunks]

    def search(self, query, k=5):
        q = trigrams(query)
        if not q:
            return []
        scored = sorted(((jaccard(q, s), i) for i, s in enumerate(self.sets)),
                        key=lambda t: (-t[0], self.chunks[t[1]].chunk_id))  # ties: chunk id, ascending
        return [(self.chunks[i], score) for score, i in scored[:k] if score > 0]
