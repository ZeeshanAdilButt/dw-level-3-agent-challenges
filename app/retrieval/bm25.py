"""BM25 through SQLite FTS5 (shipped in the starter). SQLite's bm25() is lower for a better match."""
import sqlite3


class BM25:
    def __init__(self, chunks):
        self.chunks = chunks
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE VIRTUAL TABLE c USING fts5(text, tokenize = \"porter unicode61\")")
        self.db.executemany("INSERT INTO c(rowid, text) VALUES (?, ?)", [(i, ch.text) for i, ch in enumerate(chunks)])

    def search(self, query, k=5):
        cleaned = "".join(ch if ch.isalnum() else " " for ch in query.lower())
        words = [w for w in cleaned.split() if len(w) > 1]
        if not words:
            return []
        match = " OR ".join('"' + w + '"' for w in words)
        rows = self.db.execute("SELECT rowid, bm25(c) FROM c WHERE c MATCH ? ORDER BY bm25(c), rowid LIMIT ?",
                               (match, k)).fetchall()
        return [(self.chunks[r], -s) for r, s in rows]
