# Challenge 3, part 2: the verdict and the decision

In part 1 you screened four retrievers and started one full run. Here you read that run against its parent, check it against the cost budget, decide to keep or revert it, and explain the run in five lines. The worked company is Juniper Lane Clinic. The clinic data is synthetic. A real clinic needs clinical and legal review that this course does not give.

Run every command from the repository root.

## The idea, from zero

A full run asks the chat model all the questions with one retriever. It is compared with its parent, the last kept run, which differs in one setting: the retriever. For each question the grader says pass or fail for the run and for its parent. A question that failed in the parent and passes now is **fixed**. One that passed and fails now is **broken**. The two sets are compared with a two-sided exact sign test: if there were no real difference, fixed and broken would each be as likely as heads or tails. The verdict is one of three phrases: "evidence of improvement on this set", "evidence of harm" or "inconclusive". Part of the rule is a budget: lab 3 allows p95 latency (the time the slowest 1 answer in 20 is under) to rise by at most 1 second.

Why the panel first? A bar for each slice shows where a retriever is strong, and an `n` beside each bar shows how many questions stand behind it. A slice of 8 questions moves 12 points when one question flips. You write the panel while the run finishes, because its test reads fixture records and not your run.

## Step 1: the retriever panel (20 minutes)

File: [dashboard/panels/recall-slices.js](../../../dashboard/panels/recall-slices.js#L8), the block between `// YOUR TURN start` and `// YOUR TURN end`. You wrote this block in lab 2, where it shows context fact recall by slice. Extend it now and keep what lab 2's test reads.

A screen record `runs/s0NN/cases.jsonl` has one line per screened question, with `slices` (a list), `recall3`, `recall5`, `rr` (the reciprocal rank used by MRR) and `context_fact_recall`. The panel is called with `ctx.run` (the selected run) and `ctx.cases` (its lines). Draw:

- a title that says the bars are recall at 5 by question slice;
- one row per slice with the number of questions `n`, the mean recall at 5 as a percentage and a bar for that mean;
- the other numbers (recall at 3, MRR, context fact recall) in a plain table, so a reader without the bars still gets every number.

Two helpers are shipped: [L.barTable](../../../dashboard/lib.js#L211-L222) draws a table whose last column is a bar, and [L.pct](../../../dashboard/lib.js#L41) turns 0.5 into "50%". A missing number must show as "n/a", never 0%. To compare retrievers, open the dashboard (`python -m app`, then `http://localhost:8000/dashboard`) and pick each of the four screens in the run selector. The selector shows what each screen changed.

```bash
python -m pytest challenges/challenge-3-retrieval/part-2-verdict-and-decision -q -k retriever_panel
```

The test draws your panel for two fixture screens (BM25 and vector, the same five questions) in a small fake page, and checks the `n` and the recall at 5 of each slice. Until the title and the bars say recall at 5 it fails with `AssertionError: the panel must say that its bars are recall at 5`. It needs Node.js 18 or later, the same Node that runs the dashboard tools.

## Step 2: read the result (15 minutes)

The candidate's run from part 1 should be finished now. Read it three ways.

**The diff against its parent (5 minutes).**

```bash
python -m harness diff <candidate-run> <last-kept-run>
```

[The command](../../../harness/diff.py#L99-L126) regrades both runs from their stored outputs with the current grader, checks that the two runs are comparable (same pack, same question set, same model, at most one setting different), then prints: the answer success of each on the questions both scored, `fixed`, `broken`, the ties it dropped, the sign-test p and the verdict against the named baseline. If it prints `NOT COMPARABLE`, no verdict is given: read the reason before anything else.

**Latency and cost (5 minutes).** Open the dashboard and choose the candidate as the run and the parent as the comparison. The headline panel ([dashboard/panels/headline.js](../../../dashboard/panels/headline.js#L25-L41)) lists p50 and p95 latency and the cost per answer for both, and the change. Latency p95 comes from the wall-clock time of each case (its end minus its start). A full run does not reuse cached question embeddings, so every question pays for its embedding, as it would for a new customer question. Cost per answer is the hosted-equivalent price of the tokens of each answer; a local run shows it too, so runs on both paths compare.

**Wins, ties and losses (5 minutes).** Put the diff next to your part 1 screens. The screen counted questions where recall at 5 got better, stayed the same or got worse against BM25 for each slice. The diff counts questions where the whole answer got fixed or broken. They are different measures of the same change, and they need not agree: a retriever can find a gold document and the model can still answer wrongly.

## Step 3: decide, log and explain (13 minutes)

**The rule (2 minutes).** Write it in your own words in `LAB-LOG.md` first. It is the rule from lab 2, plus the budget:

1. Verdict "evidence of improvement on this set" and p95 within +1 second of the parent: keep.
2. Verdict "inconclusive": keep only if the candidate is cheaper or simpler than the parent. A retriever that calls an embedding model is neither, so the parent stays.
3. Verdict "evidence of harm", or p95 more than 1 second over: revert.

**The log (4 minutes).** Add a section titled `## Lab 3: retrieval` to `LAB-LOG.md` with five labelled lines: `Claim:`, `Evidence:`, `Cost:`, `Next:` and `Decision:`. `Evidence:` names your run ids (the candidate, the parent and your four screens), and each id must be a folder in your own `runs/`.

**Explain the run (5 minutes).** The same five lines are the explanation. Write them in the order claim, evidence, cost, next, decision:

- Claim: the retriever you kept or reverted, with the verdict word and the run it was compared with.
- Evidence: the run ids, the fixed and broken counts, the slice with the largest win, and any slice that lost, each with its `n`.
- Cost: the p95 change against the 1 second budget, and the change in cost per answer.
- Next: "try one link hop in lab 4."
- Decision: keep or revert, and the command you ran.

**Commit (2 minutes).** Keep or revert with the harness, so `runs/kept.json` and `config/settings.toml` change together, then commit both with the log:

```bash
python -m harness keep <candidate-run>
```

Run `python -m harness revert <candidate-run>` if the decision is revert. Plain `python -m harness revert` with no run id undoes the last kept run, which is not what you want for a candidate you never kept. A well-argued revert completes the lab. Then run the part's tests:

```bash
python -m pytest challenges/challenge-3-retrieval/part-2-verdict-and-decision -q
```

`test_decision_logged` checks the lab 3 entry for the five lines, for at least one run id, for run ids that exist in your `runs/`, and for the word keep or revert on the `Decision:` line. Without a lab 3 entry it fails with `AssertionError: LAB-LOG.md has no lab 3 entry`. `test_shell_serves_runs` passes on the starter and keeps passing: the dashboard shell still serves your runs.

Last, check the lab:

```bash
python -m harness gate 3
```

[The gate](../../../harness/gate.py#L84-L150) reads your own records only. It checks that your work is committed, that a complete full run exists, that your prediction was committed before your first record, that screens and run share every setting but the retriever, that all four retrievers were screened, that the run is comparable with its parent, that a keep or revert decision is recorded (a missing one is a warning, and the gate then expects the run id in `LAB-LOG.md`), and that `results.md` cites only your own runs. The shape of your lab 3 entry is checked by `test_decision_logged`.

## Reference results (Juniper Lane Clinic)

| Measure | Value |
|---|---|
| Candidate | hybrid |
| Answer success, parent | 31% |
| Answer success, candidate | 31% |
| Fixed | 3 |
| Broken | 3 |
| Verdict | inconclusive |
| p95 change, seconds | 1.2 |
| Cost per answer change | -$0.0000 |
| Reference decision | revert |

The same numbers for the other two companies, from the same chain of runs:

| Company | Candidate | Verdict | p95 change, seconds | Decision |
|---|---|---|---|---|
| Quillon | vector | inconclusive | 1.0 | revert |
| Saltmarsh Mutual | vector | inconclusive | 1.7 | revert |

Juniper Lane's screens, recall at 5 (percent):

| Retriever | Code | Typo | Paraphrase |
|---|---|---|---|
| BM25 | 100 | 75 | 20 |
| Hybrid | 89 | 75 | 70 |

These are measured on the synthetic packs and are a prediction to test on your own pack, not a rule.
