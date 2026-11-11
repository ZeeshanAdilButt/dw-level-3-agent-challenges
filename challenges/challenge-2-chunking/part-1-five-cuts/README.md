# Challenge 2, part 1: five cuts, one candidate

You write two ways to cut a document, write the number that measures a cut, screen five settings on your company's pack, find two kinds of damage a cut can do, and start one full run. Run every command from the repository root. The packs are synthetic; a real clinic would need clinical and legal review that this course does not give.

## The idea, from zero

The agent cannot read 150 documents for every question, so the corpus is cut into **chunks** and the retriever returns a few. Where you cut decides what the model sees. Cut too small and a fact loses its label: a table row arrives without its header, or a sentence arrives without the heading that says which plan it is about. Cut too big and each chunk holds more than one idea, so fewer chunks fit under the budget. A **token** here is a word or one punctuation mark ([`count_tokens`](../../../app/retrieval/corpus.py#L11-L13)); it approximates the model's own tokens.

The number that measures a cut is **context fact recall**: the share of a question's key facts that are present, with their qualifiers, in the text delivered to the model. "Delivered" means after the global budget of 3,000 tokens ([the assembly](../../../app/context.py#L138-L139)). A fact cut off by the budget counts as missing. You wrote recall at 5 in lab 1; it counts gold documents among the ranked chunks. Context fact recall counts facts in the text. Both matter, because a chunk from the right document can still lack the sentence with the answer.

## Step 1: two chunkers (30 min)

Run the tests and read the failures (4 min):

```bash
python -m pytest challenges/challenge-2-chunking/part-1-five-cuts -q
```

File: [`app/retrieval/chunkers.py`](../../../app/retrieval/chunkers.py). Every chunk keeps its document id, its heading and its position ([`Chunk`](../../../app/retrieval/chunkers.py#L11-L17)); a chunk id is `<doc id>#<position>`.

**Cut with overlap (13 min), [`chunk_with_overlap`](../../../app/retrieval/chunkers.py#L46-L51) with [`_split_tokens`](../../../app/retrieval/chunkers.py#L20-L33). The names `fixed` and `by_heading` stay as aliases, so the shipped code and the tests keep working.** Cut the body into windows of `size` tokens. The start positions step by `size - overlap`, so consecutive chunks share exactly `overlap` tokens. The chunks cover the whole document, and the last chunk is the first one that reaches the end of it (the loop stops there; it never adds a chunk that only repeats the tail). An empty document gives no chunks, and a document shorter than `size` gives one. Keep the original spacing, because a table row must stay a table row. An overlap that is not below the size is rejected by the shipped settings validator ([`settings.py`](../../../app/settings.py#L95-L96)) before any chunker runs.

Worked example, ten tokens `w0 ... w9`, size 4, overlap 2: starts 0, 2, 4, 6 give `w0-w3`, `w2-w5`, `w4-w7`, `w6-w9`. With overlap 0 the same text gives `w0-w3`, `w4-w7`, `w8-w9`. With overlap 3 (one below the size) the step is 1 and you get 7 chunks.

**Cut by heading (13 min), [`chunk_by_heading`](../../../app/retrieval/chunkers.py#L76) (the `def` in the file is named `by_heading`; keep that name, because `chunk_by_heading` is an alias set below the block) with [`sections`](../../../app/retrieval/chunkers.py#L58-L69).** Split on Markdown headings (`#` to `######`). A chunk never crosses a heading. A section longer than `max_size` tokens is cut by size, and every piece keeps its heading: a piece that does not start with the heading line gets the heading text put in front of it, and the heading counts toward `max_size`. Text before the first heading is a section titled with the document title, and a document with no headings is one chunk.

Rerun the tests when each one is written. `test_chunkers` pins the boundary values: overlap 0, overlap one below the size, an empty document and a document shorter than the size.

## Step 2: context fact recall (15 min)

Read how recall at k is written in [`recall.py`](../../../harness/graders/recall.py#L35) (3 min). Then write [`context_fact_recall`](../../../harness/graders/fact.py#L21-L22) (8 min). It takes the delivered text and the key facts and returns `(found, total, per_fact)`. It reuses your `check_fact` from lab 1 with the rival test switched off, because the delivered text may hold an old value of the same attribute and the grader of the reply, not of the evidence, is what rejects a wrong value. Rerun the tests (4 min). `test_context_fact_recall` uses fixed texts: a fact cut off by the budget is missing, a table row split from its header loses its qualifier, and an old value in the evidence does not stop a fact from counting.

Where the screen's number comes from: [`_agg`](../../../harness/screening.py#L38-L50) adds the facts found and the facts total over every question and divides, so the `facts` count in a screen is the `n` behind the recall. Context tokens per answer is the mean of the tokens delivered to the model.

## Step 3: predict, screen, find, commit, start (25 min)

**Predict (3 min).** In `predictions/lab2-chunking.md` write which of the five settings will have the highest context fact recall, whether its full run will show evidence, harm or neither, and how many context tokens per answer you expect the overlap setting to add. Commit and push it before the first screen.

**Screen five settings (5 min).** Each takes its other settings from your last kept run (the baseline of lab 1) and changes one thing ([`run_screen`](../../../harness/screening.py#L126-L183)). A screen calls no chat model and takes 1 seconds.

```bash
python -m harness screen --pack <your-pack> --set chunker=fixed --set chunk_size=200
python -m harness screen --pack <your-pack> --set chunker=fixed --set chunk_size=400
python -m harness screen --pack <your-pack> --set chunker=fixed --set chunk_size=800
python -m harness screen --pack <your-pack> --set chunker=heading --set chunk_size=400
python -m harness screen --pack <your-pack> --set chunker=fixed --set chunk_size=400 --set overlap=80
```

The 400 setting is the baseline, so it changes nothing. For `heading`, 400 is the section limit.

**Read (5 min).** For each screen note context fact recall, context tokens per answer, and the `table` and `far-from-heading` slices with their `n`. Reference, for each company:

| Company | 200 | 400 (baseline) | 800 | Heading 400 | Overlap 80 | Candidate |
|---|---|---|---|---|---|---|
| Quillon | 47% | 53% | 51% | 46% | 54% | Fixed 400, overlap 80 |
| Juniper Lane | 52% | 59% | 58% | 53% | 58% | Fixed 400, overlap 80 |
| Saltmarsh | 60% | 67% | 66% | 54% | 63% | Fixed 400, overlap 80 |

Context tokens per answer for the same settings: Quillon 956, 1716, 2726, 631 and 1786.

**Find the damage (4 min).** The screen stores the delivered chunk ids of every question in `runs/<screen-id>/cases.jsonl`. Look at the chunks themselves.

A **split table** is a delivered chunk that starts in the middle of a table, so its rows have no header. Run this on a `table` question's row:

```python
import json
from app.retrieval.corpus import load_corpus
from app.retrieval.chunkers import chunk_corpus

docs = load_corpus("packs/<your-pack>")
chunks = {c.chunk_id: c for c in chunk_corpus(docs, "fixed", 400, 0)}
for line in open("runs/<baseline-screen-id>/cases.jsonl", encoding="utf-8"):
    row = json.loads(line)
    if "table" in row["slices"]:
        for cid in row["delivered"]:
            lines = chunks[cid].text.lstrip().splitlines()
            if lines[0].startswith("|") and not (len(lines) > 1 and lines[1].lstrip().startswith("|--")):
                print(row["id"], cid, lines[0][:60])
```

A **lost heading** is a delivered chunk of a gold document that holds a gold fact but no heading line, so the model cannot tell which section the fact belongs to. The gold facts of a question sit at character offsets in its document (`gold_spans` in `packs/<your-pack>/eval/questions.jsonl`). Take a `far-from-heading` question, find its gold document, and print the delivered chunks of that document that have no line starting with `#` (use [`HEADING`](../../../app/retrieval/chunkers.py#L7)). A piece that your heading cut put the heading in front of starts with the heading text, without hash signs, so count it as having its heading. Look in a screen of the fixed cut: your `chunk_by_heading` puts the heading at the top of every piece, so the heading setting should show no lost heading at all. A table header row is different: neither cut repeats it. Write the two case ids down.

**Choose and start (5 min).** The candidate is the changed setting with the highest context fact recall within the lab's token budget (up to 25 percent more context tokens than the baseline). The simpler setting wins a tie. It is always a changed setting: if the baseline has the highest recall, you still run the best of the four, and part 2 will most likely revert it, which completes the lab.

Write `results.md` in this folder: a table with the columns `Setting | Screen run | Context fact recall | Context tokens | Key facts`, one row for each of the five screens (the screen run is its run id, for example `s004`), then three lines:

```
split table case: <question id>
lost heading case: <question id>
candidate: <setting>
```

Commit the code and `results.md`, because a run starts only from a committed tree (the prediction was committed before the first screen and stays untouched). Then start the candidate's full run. It takes the parent's settings and changes only what you name:

```bash
python -m harness run --pack <your-pack> --set <the candidate's overrides> --parent <last-kept-run>
```

The run takes about 13 minutes with a GPU and about 29 minutes (estimated) on the CPU only for Quillon. If it stops, `python -m harness run --resume` continues it. The run works from its own snapshot, so edits cannot change it.

**The decision rule, printed once in this course, in the roadmap's words.** Keep a change only if the full run shows evidence of improvement and its extra cost stays within the lab's budget, or the log argues for going over it. Keep a change with no evidence either way only if it makes the agent cheaper or simpler, counted as fewer settings, calls or components. Otherwise revert, and a well-argued revert completes the lab. Part 2 applies it.

## The tests

- Acceptance, failing on the starter: `test_chunkers` and `test_context_fact_recall` (`NotImplementedError: YOUR TURN: ...`), and `test_results_table` (`AssertionError: results.md has no screen table`). `test_results_table` passes when the five rows and the two case ids agree with your own screen records: each row's key-fact count equals its record's, each recall and token count equals that record's value, the five records are the five settings above, and each found case is a question of the right slice in your screens.
- Invariant, passing on the starter: `test_settings_validator` (an overlap that is not below the size is rejected) and `test_the_results_checker_on_fixed_records`.

## If something looks wrong

- **Overlap 80 gives fewer chunks than overlap 0.** Your step is `size + overlap` instead of `size - overlap`.
- **The last chunk repeats the tail of the one before it.** Stop at the first window that reaches the end.
- **By heading gives one huge chunk.** Your section limit is not applied to long sections, or the heading pattern requires a space the document does not have.
- **A screen row says `n/a` for context fact recall.** A question with no key facts has none; the screen skips it.
