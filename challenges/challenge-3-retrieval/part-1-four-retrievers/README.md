# Challenge 3, part 1: four retrievers

You write three small retrievers, then screen four retrievers on your company's pack. A screen calls no chat model, so it takes seconds and gives the same numbers every time. Run every command from the repository root.

## The idea, from zero

A retriever takes a question and returns the chunks most likely to hold the answer. The agent never sees the rest of the pack, so a gold document that is not in the top five is a document the answer cannot cite. BM25 (lab 1) ranks chunks by the words they share with the question. It cannot see a typo, and it cannot see that "refund" and "money back" mean the same thing. Three other ways to rank:

1. **Trigram similarity.** Cut every word into pieces of three characters and compare the two piece sets. "refund" and "refunds" share most pieces, so a typo still matches. It matches characters, not meaning.
2. **Vector search.** An embedding model turns text into a list of numbers so that texts with similar meaning get similar lists. Rank chunks by the angle between the question's list and each chunk's list. It matches meaning, and it can lose an exact code.
3. **Hybrid fusion.** Ask two retrievers for a top 20 each. Give every chunk a score from each list it is in, and add the scores. A chunk that is fairly high in both lists beats a chunk that is first in one and far down the other.

## Step 0: run the tests and read the failures

```bash
python -m pytest challenges/challenge-3-retrieval/part-1-four-retrievers -q
```

On the starter you see three failing tests (`test_trigram`, `test_fusion`, `test_vectors`), each ending in `NotImplementedError: YOUR TURN: ...`. The tests use fixed inputs only: no model, no pack, no reference numbers.

Then build the vector index so it is ready later. It embeds every chunk once and caches the vectors under `.cache/embeddings/`:

```bash
python -m harness index --pack <your-pack>
```

It prints the chunk count and the seconds it took. On the reference laptop, Quillon's 293 chunks were embedded once and cached (the reference build did not time this step). Your count is different if your lab 2 chunking is different.

## Step 1: trigram similarity

File: [app/retrieval/trigram.py](../../../app/retrieval/trigram.py#L6-L12) for `trigrams`, [the search](../../../app/retrieval/trigram.py#L25-L31) for the ranking.

- Normalise with Unicode NFKC and lowercase, so a capital or a full-width letter does not change the pieces.
- Split into words of letters and digits. Punctuation only separates words.
- Pad each word with two spaces in front and one behind, then take every piece of three characters. For "refund" the pieces are `"  r"`, `" re"`, `"ref"`, `"efu"`, `"fun"`, `"und"`, `"nd "`.
- Score by Jaccard, the shared pieces divided by all the pieces in both sets ([the helper](../../../app/retrieval/trigram.py#L15-L17)). "refund" and "refunds" share 6 pieces of 9, so the score is 0.667.
- Sort by score, break a tie by chunk id as text (smallest first), keep the top k with a score above zero.

## Step 2: reciprocal rank fusion

File: [app/retrieval/fusion.py](../../../app/retrieval/fusion.py#L11-L18).

Ask each retriever for its top 20 (`depth`). For every chunk add `1 / (60 + rank)` from each list it is in, with rank 1 for the first chunk. A chunk that is not in a list gets nothing from it. Sort by the total, break a tie by chunk id as text, keep the top k. Do not weight the lists. The constant 60 is the value that the paper that introduced the method used (Cormack, Clarke and Buettcher, 2009), so you do not tune it.

Worked numbers: a chunk at rank 1 in one list and rank 2 in the other scores 1/61 + 1/62, which is 0.03252. A chunk first in one list and 20th in the other scores 1/61 + 1/80, which is 0.02889. A chunk second in both scores 1/62 + 1/62, which is 0.03226, so it wins.

```bash
python -m pytest challenges/challenge-3-retrieval/part-1-four-retrievers -q -k "trigram or fusion"
```

Commit when both pass.

## Step 3: vector search

File: [app/retrieval/vectors.py](../../../app/retrieval/vectors.py#L51-L55). The starter gives you [`embed(texts, prefix)`](../../../app/retrieval/vectors.py#L24-L39), a `self._embed(texts, prefix)` that calls it with the embedding model from your settings (use that one for the question, so a changed `embed_model` setting takes effect), and the stored vectors.

Embed the question with the prefix `search_query: `. (The chunks were embedded with `search_document: `; the model was trained with those two prefixes.) Scale both vectors to length 1 ([`_norm`](../../../app/retrieval/vectors.py#L42-L44)); the dot product of two length-1 vectors is their cosine similarity. Sort by that score, break a tie by chunk id as text, keep the top k.

```bash
python -m pytest challenges/challenge-3-retrieval/part-1-four-retrievers -q -k vectors
```

`test_vectors` replaces `embed` with three fixed vectors, so it needs no model. Commit when it passes.

## Step 4: write your prediction, then screen

Before the first screen, write `predictions/lab3-retrievers.md`: which retriever you expect to lead the code slice, the typo slice and the paraphrase slice, and which one you will start in full. Commit and push it. A run record stores the prediction commit, and the examiner reads the push time from GitHub.

The four names are already wired into the `retriever` setting in [app/retrieval/index.py](../../../app/retrieval/index.py#L62-L72):

```bash
python -m harness screen --pack <your-pack> --set retriever=bm25
python -m harness screen --pack <your-pack> --set retriever=trigram
python -m harness screen --pack <your-pack> --set retriever=vector
python -m harness screen --pack <your-pack> --set retriever=hybrid
```

Each screen takes its other settings from your last kept run, writes a new record under `runs/` and prints recall at 5, recall at 3, MRR at 5, evidence-span coverage and context fact recall, overall and by slice, each with its number of questions. After the BM25 screen it also prints wins, ties and losses against BM25 ([the count](../../../harness/screening.py#L77-L91)).

Where each number comes from:

- **Recall at 5**, per question: the gold documents found in the top five, divided by that question's gold documents. A slice's number is the mean over its questions. The questions come from `packs/<your-pack>/eval/questions.jsonl`; a question needs retrieval and at least one gold source to be screened ([the filter](../../../harness/screening.py#L98)).
- **MRR at 5**: 1 divided by the rank of the first chunk from a gold document, 0 when none is in the top five, averaged.
- **Win, tie, loss**: for one question, the retriever's recall at 5 against BM25's recall at 5 on the same question. Higher is a win, equal a tie, lower a loss.
- A slice has few questions (see the table), so one question moves its percentage by many points. Read the counts.

## Step 5: choose one candidate and start its full run

The candidate must be trigram, vector or hybrid, because a full run tests one change against its parent and BM25 is the parent. Choose with two things: the slices that matter for your company, and cost (vector search and hybrid embed every new question; part 2 checks that p95 latency rises by at most one second).

Write a table of your four screen run ids and the candidate, with a two-sentence reason, in `results.md` in this folder. Commit it with your prediction. Then start the run:

```bash
python -m harness run --pack <your-pack> --set retriever=<candidate> --parent <last-kept-run>
```

When it has finished, check the part with `python -m harness gate 3 --part 1`. Until the full run is complete the receipt prints a `FAIL` line for it, which is expected here. The gate checks that the work is committed, that all four retrievers were screened, that the prediction was committed before the first record, that `results.md` exists and cites only run ids you have, and it lists the other checks it makes. The run takes 13 minutes with a GPU and about 29 minutes (estimated) on the CPU only, for Quillon, and works from a copy of your last commit, so you can keep editing.

## Reference results (Quillon, 400-token chunks)

| Retriever | All | Code | Typo | Paraphrase | MRR |
|---|---|---|---|---|---|
| BM25 | 73% | 100% | 50% | 30% | 0.494 |
| Trigram | 47% | 63% | 50% | 10% | 0.149 |
| Vector | 85% | 75% | 100% | 80% | 0.534 |
| Hybrid | 84% | 100% | 88% | 60% | 0.525 |
| Questions | 62 | 8 | 8 | 10 | |

Wins-ties-losses against BM25 on Quillon:

| Against BM25 | Code | Typo | Paraphrase |
|---|---|---|---|
| Trigram | 0-5-3 | 2-4-2 | 0-8-2 |
| Vector | 0-6-2 | 4-4-0 | 5-5-0 |
| Hybrid | 0-8-0 | 3-5-0 | 3-7-0 |

The best retriever on codes and on paraphrases for the other two companies:

| Company | Best on codes | Best on paraphrases |
|---|---|---|
| Juniper Lane Clinic | BM25 | hybrid |
| Saltmarsh Mutual | vector | vector and hybrid (tied) |

These are measured on the synthetic packs. They are a prediction to test on your own pack, not a rule.

## If a number looks wrong

- Vector recall is below BM25 on paraphrases: check the two prefixes, then that both vectors are length 1, then that the index was built with the embedding model the search uses.
- Every trigram score is near 0.05: that is expected on 400-token chunks. If every score is exactly 0 for a question that shares words with the pack, the padding or the split is wrong: run `test_trigram`.
- Hybrid equals vector search on every question: check one question's two lists. If they differ, check that fusion asks each list for 20, not 5.
- The numbers differ from this README: your chunking, the embedding model version or the pack differs. Trigram, vector and fusion break ties by chunk id as text; BM25 by the order chunks were stored.
