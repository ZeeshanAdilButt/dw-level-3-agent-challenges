"""Reciprocal rank fusion: add 1 / (60 + rank) from each list."""

K = 60


class Hybrid:
    def __init__(self, *retrievers, depth=20):
        self.retrievers = retrievers
        self.depth = depth

    def search(self, query, k=5):
        scores, keep = {}, {}
        for r in self.retrievers:
            for rank, (ch, _) in enumerate(r.search(query, self.depth), start=1):
                scores[ch.chunk_id] = scores.get(ch.chunk_id, 0.0) + 1.0 / (K + rank)
                keep[ch.chunk_id] = ch
        best = sorted(scores.items(), key=lambda t: (-t[1], t[0]))[:k]  # ties: chunk id, ascending
        return [(keep[cid], s) for cid, s in best]
