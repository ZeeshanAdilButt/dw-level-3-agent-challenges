# Challenge 4, part 1: three ways to add context

You add three ways to give the model more than the five chunks that ranked highest: the chunks beside a hit, the whole section a hit sits in, and the documents a hit's document links to. Then you put everything together under one token budget, screen the four settings and start one full run. The worked company is Juniper Lane Clinic; the packs are synthetic, and a real clinic needs clinical and legal review that this course does not give. Run every command from the repository root.

70 work minutes. A screen takes seconds. Step 9 starts a full run that finishes after the part: 13 minutes with a GPU and about 29 minutes (estimated) on the CPU only, on the reference laptop for Juniper Lane. Part 2 reads it after its first steps, so this part adds no waiting.

## The idea, from zero

A retriever returns chunks, and a chunk is a cut of a document. The answer is often just outside the cut: the rule is in the chunk, the exception is in the next one, the heading that says which product it is about is in the one before. There are three cheap ways to widen what the model reads:

- **Neighbours.** Add the chunks before and after each hit in the same document.
- **Section parent.** Add the whole section, from its heading to the next heading, that holds the hit.
- **Link hop.** Add the best chunk of each document that the hit's document links to (its `links` front matter). One level only: a linked document's own links are not followed.

Everything you add costs tokens, and the model has a limit. So the context has three stages, and the contract names them:

1. **Ranked hits**: what the retriever returned.
2. **Expanded evidence**: what the expansion added.
3. **Delivered text**: ranked hits first, then the expansions in the order they were found, duplicates removed (a section parent replaces the hits it contains), cut at one global limit (`context_token_limit`, 3,000 tokens by default).

A **citation** is valid when its document is in the delivered evidence. That includes a section parent or a linked document, and excludes a document that was found but cut before delivery.

A linked document is a new document. It could be one the person may not see, so the hop asks the access check `allowed(item, principal)` for each target and drops the target when the answer is no. The shipped `allowed` returns true until lab 7, so nothing is refused today; the call must still be there, because lab 7 turns it on.

## Step 1: write and push your prediction (5 minutes)

In `predictions/lab4-context.md` write: which setting will give the highest context fact recall, which will cost the most tokens, and whether any setting will go more than 50 percent above the parent in tokens. Commit and push it before any screen. The gate reads the commit time.

## Step 2: read the parent and draw the panel (8 minutes)

The parent is the last kept run in `runs/kept.json`. Its record shows the context tokens per answer. The panel [dashboard/panels/context-tokens.js](../../../dashboard/panels/context-tokens.js#L8) is empty on the starter ("Panel not built yet"). Write it so that it shows, for the selected run and for its comparison run: the run id, the mean delivered tokens per answer, the number of cases behind it (`n`), the largest answer and how many were cut by the budget. The data per case is `context_tokens` in `cases.jsonl` (the delivered text, after the cut) and `truncated` in the final step's eval block. Two shipped helpers: `L.contextTokensOf(case)` and `L.finalEval(case)`. Writing this panel with an assistant is allowed. Read what it wrote.

For Juniper Lane the reference baseline is 1814 tokens per answer. For the other two companies: Quillon 1716, Saltmarsh 1807.

## Step 3: neighbours (10 minutes)

File: [app/context.py](../../../app/context.py#L80-L81), `_neighbours(index, hit, n)`.

`index.by_doc[doc_id]` holds the chunks of one document in order. Find the hit's place `i`. For each distance 1 to `n`, take the chunk at `i - distance` and at `i + distance`, if the place exists. Stop at the edge: the first chunk has nothing before it, the last has nothing after it. `n` is `neighbours_n` in [config/settings.toml](../../../config/settings.toml#L34), 1 by default.

## Step 4: section parent and assembly (12 minutes)

Section parent, [app/context.py](../../../app/context.py#L81-L85): `_sections(doc)` ([L51-L61](../../../app/context.py#L51-L61)) already gives the character range of each heading section. Find the range that holds the hit's text, and return one new chunk whose text is the whole section. Give it an id of its own (`<doc>#sec<k>`) so it can never be mistaken for an ordinary chunk. If the section is the hit's own text, return nothing: there is nothing to add.

Assembly, [app/context.py](../../../app/context.py#L199-L201), the block between `# YOUR TURN start` and `# YOUR TURN end` inside `retrieve`:

- start from `candidates`, the ranked hits then the expansions in the order they were found, already filtered by authority;
- skip a chunk whose text was already delivered (a neighbour that is also a hit); a section parent that holds hits already delivered takes their place once, and their tokens are freed;
- the authority call is already written above the block: when `authority_rule` is `on` it calls `apply_authority` (part 2 writes it), keeps `res.conflict` and `res.dropped_docs`, and removes the dropped documents from `candidates`; the setting is off until part 2;
- keep a running total of tokens; when the next chunk would pass `context_token_limit`, cut it at the limit ([`_cut`](../../../app/context.py#L65-L68)), set `truncated`, and stop;
- the delivered tokens are the sum over what was delivered.

The expansion loop that calls your functions is already written ([L137-L138](../../../app/context.py#L137-L138)): one expansion kind at a time, chosen by the `context` setting.

## Step 5: one link hop (13 minutes)

File: [app/context.py](../../../app/context.py#L88-L89), `_linked(index, hit, query, allow)`.

For each document in the hit's document's `links`: skip it if it does not exist or links to itself; ask `allow(...)` for the target (this is `allowed(item, principal)` bound to the asking principal) and skip it if the answer is no; take the target's chunk that shares the most words with the question. Do not look at the targets' own links: one hop. When the access defence is off, `allow` is `None` and nothing is asked.

## Step 6: run the tests (5 minutes)

```bash
python -m pytest challenges/challenge-4-related-docs/part-1-three-ways-to-add-context -q
```

[test_context.py](test_context.py) writes a three-document pack into a temporary folder and checks, with the stub model and no reference numbers: neighbours stop at the edge of a document; the section parent is the whole heading section and nothing from the next one; assembly puts ranked hits first, then expansions in order, removes duplicates and applies one global limit, and logs the cut; a citation to a delivered document (a parent or a linked one) is valid and one to a document that was not delivered is not; the hop asks the access check for each target and drops a refused one (tested with a fake that returns false); the hop follows one level only. On the starter each fails with `NotImplementedError`. Fix what fails and commit.

## Step 7: screen four settings (10 minutes)

```bash
python -m harness screen --pack <your-pack> --set context=none
python -m harness screen --pack <your-pack> --set context=neighbours
python -m harness screen --pack <your-pack> --set context=section_parent
python -m harness screen --pack <your-pack> --set context=link_hop
```

A screen calls no chat model. For each setting it prints, overall and by slice with the number of questions: recall at 5 (on the ranked hits, which expansion does not change), context fact recall (the share of key facts that appear, in an accepted form, anywhere in the delivered text) and the mean delivered context tokens. [The screen code](../../../harness/screening.py#L94-L123) reads them from the delivered text, after the budget.

Write `results.md` in this folder: a table with four rows (one per setting) and these columns: context fact recall, ranked-hit recall at 5, context tokens, and the question ids that moved. Add the `linked-doc` slice as its own row for each setting, with its `n`. A screen is exact and has no verdict: it shows a change, not whether the answers improved.

Reference numbers for Juniper Lane:

| Setting | Context fact recall | Context tokens |
|---|---|---|
| none | 59% | 1814 |
| neighbours | 60% | 2769 |
| section_parent | 59% | 2259 |
| link_hop | 62% | 2909 |

The `linked-doc` slice has 10 questions for Juniper Lane. 2 internal documents were followed by the hop with the access check off. That count is why lab 7 matters. The same two tables for Quillon and Saltmarsh are in the course facts; they are measured on the synthetic packs, and they predict, not prove, what your pack does.

## Step 8: pick one candidate (3 minutes)

The candidate is always a changed setting: `neighbours`, `section_parent` or `link_hop`. Choose the one with the highest context fact recall that stays within 50 percent more tokens than the parent (the `none` row). On a tie, the one with fewer tokens. Write the reason in one line in `results.md`, and one line saying that you chose on the same questions the full run will read, so the choice has a small head start. If the screen favours `none`, still run the best changed candidate: part 2 will most likely revert it, and that completes the lab.

## Step 9: commit and start the full run (4 minutes)

```bash
git add -A
git commit -m "Lab 4 part 1: three ways to add context"
python -m harness run --pack <your-pack> --set context=<candidate> --parent <last-kept-run>
```

The `git add -A` is needed because `results.md` is a new file, and `git commit -am` skips new files. The harness then refuses to run with untracked files outside `runs/` and `.cache/`.

The run prints its resolved settings first. Check that only `context` differs from the parent. While it runs, read four questions the screen moved: open `runs/s0NN/cases.jsonl`, find a question whose `delivered` list differs between two settings, and read the added text.

## Where the numbers come from

- Delivered tokens: the sum of `tokens` of the chunks that were delivered. A chunk's tokens are the count of words and punctuation marks in its text (`count_tokens`, [app/retrieval/corpus.py](../../../app/retrieval/corpus.py#L11-L13)). It approximates the model's own tokens.
- Context fact recall: key facts found in the delivered text divided by all key facts of the questions in the group, with an accepted spelling counted ([the grader](../../../harness/graders/fact.py)).
- The 50 percent budget: delivered tokens of the candidate divided by delivered tokens of the parent, minus 1.
