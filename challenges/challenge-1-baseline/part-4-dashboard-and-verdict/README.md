# Challenge 1, part 4: the dashboard and the first verdict

You read the three runs from part 3, write the run tree and the diff panel, read the first verdict, mark run 1 as your baseline, and write the lab 1 entry in your log. Start this part in a new sitting, after the three runs have finished. Run every command from the repository root. The data is synthetic.

## The idea, from zero

The dashboard is a page that reads the files under `runs/` and shows them as tables. It does no grading of its own: every number on it comes from `run.json` or `cases.jsonl`, which the harness wrote. Its job is to answer two questions fast. What did this run score, and what changed against the run it came from?

Three words first. A **token** is a piece of text a model reads and bills. **Cost per answer** is tokens in times the input price plus tokens out times the output price, from the dated price file ([`config/prices.toml`](../../../config/prices.toml); a local run pays zero and shows the hosted-equivalent price). **p50** is the median answer time. **p95** means 95 in 100 answers are faster than this. Both come from nearest rank: sort the times and take the value at position `ceil(p x n)` ([the page's helper](../../../dashboard/lib.js#L55-L61), [the harness's](../../../harness/util.py#L61-L66)).

Constructed arithmetic, so you can check your own code. With made-up prices of 1 dollar per million tokens in and 4 dollars per million out, 1,000 tokens in and 200 tokens out cost 0.001 + 0.0008 = 0.0018 dollars. For 100 answer times where 90 take 4 seconds, 5 take 6 and 5 take 20, position 95 holds 6 seconds, the median is 4 and the mean is 4.9. The mean hides the slow tail. If 99 take 4 seconds and one takes 60, the mean rises to 4.56 and p95 stays at 4, because the slow answer sits above position 95.

## Step 1: read the runs, the history and the headline (25 min)

1. Load your three runs from `runs/`. Read each run id, the `fingerprint` and `cache_mode` in the first record. Check that the three fingerprints are equal and that `cache_mode` is `off`. Run `python -m harness validate` (8 min).
2. The run history table is shipped: [`run-history.js`](../../../dashboard/panels/run-history.js#L1-L39) draws one row per run with its parent and change, newest first. Open `python -m app` and read `http://localhost:8000/dashboard` (9 min).
3. The headline table is shipped too: [`headline.js`](../../../dashboard/panels/headline.js#L1-L53). Read it with its `n`: answer success, cited correctly, recall at 5, security pass rate, cost per answer and p50 and p95. A number that cannot be computed shows `n/a`, never 0% ([`L.metric`](../../../dashboard/lib.js#L107-L115)). Note each `n` and say what the eligible cases are (8 min).

## Step 2: the run tree and the diff, then the first verdict (20 min)

Two panels are yours, each a block marked `// YOUR TURN` in `dashboard/panels/`. On the starter each draws "Panel not built yet". The shell calls `render(ctx, el)` with `ctx.run`, `ctx.base`, `ctx.cases`, `ctx.baseCases`, `ctx.runs` and `ctx.kept` ([`dashboard.js`](../../../dashboard/dashboard.js#L1-L11)), and [`lib.js`](../../../dashboard/lib.js#L186-L207) gives you `L.table`.

**`run-tree.js` (the small tree of runs).** [The reference block](../../../dashboard/panels/run-tree.js#L8) groups runs by parent and draws each child under its parent with an indent and a `(kept)` mark on the last kept run. A table is the layout.

**`diff.js` (the per-change diff and its verdict).** [The reference block](../../../dashboard/panels/diff.js#L8) works through the cases both runs answered:

- Keep a case only when both runs were graded on it. That is the eligible set.
- Show the counts in a table whose first column says `Fixed`, `Broken` and `Sign test p`, with the number in the second column (the test finds the rows by those words).
- **Fixed**: failed in the baseline, passes now. **Broken**: passed in the baseline, fails now. Everything else is unchanged and is dropped.
- The **sign test** asks how likely this split of fixed and broken would be if each flip were a coin toss. [`L.signTest`](../../../dashboard/lib.js#L63-L70) is two-sided and exact, and caps at 1. Ties are dropped before it is called.
- The verdict word: `evidence of improvement on this set` when p is under 0.05 and fixed is the larger; `evidence of harm` when p is under 0.05 and broken is the larger; otherwise `inconclusive`. Where each number comes from: fixed and broken are counts of case ids; p comes from those two counts; 0.05 is the harness's alpha ([`signtest.py`](../../../harness/signtest.py#L7-L30)).

Print p to three decimals ([`fmt_p`](../../../harness/signtest.py#L20-L23) does the same in the terminal) and cap it at 1.000.

Now the first verdict. Before you open the page, write down your prediction for run 2 against run 1 and for run 3 against run 1 (fixed, broken and the verdict word). Then read it on the page, and in the terminal:

```bash
python -m harness diff <run> <parent>
```

`harness diff` regrades the stored outputs of both runs with the current grader, prints the grader version, and prints the same counts and verdict, so you can check the page against it. Write the noise floor in `results.md` in this folder: cases changed, fixed and broken for each of the three pairs. The reference pairs for Quillon: 0, 0 and 0 cases changed (runs 1 to 2, 1 to 3, 2 to 3), and the verdict of run 2 against run 1 was inconclusive. If a pair shows evidence, that is the false alarm that a 0.05 test gives about one time in twenty. Say so in your log. Do not swap the pair for another.

## Step 3: the interface check and the log (15 min)

House style for this dashboard, short, and a style rather than a sourced rule: the run history and the diff are tables, and the tables are the layout, not a grid of cards. One neutral palette and one accent chosen on purpose, avoiding both the purple gradient default and its newer replacement, cream with terracotta. Real labels, not slogans. Numbers right-aligned with units. No gradients, glow or glass panels. Every chart titled with what it shows. Check your two panels against it once, and keep long dashes out of panel text (a range such as 60-70 is fine) (4 min).

Write the lab 1 entry in `LAB-LOG.md`, then **Explain the run**, three questions answered as claim, evidence, cost and next (7 min):

- Claim: the baseline answers N questions of the eligible set, and the noise floor is M cases (both from your runs).
- Evidence: the three run ids and the verdict of run 2 against run 1.
- Cost: the cost per answer and p95.
- Next: try chunking in lab 2.

The lines are yours, not an assistant's. Then mark run 1 of the three as the baseline:

```bash
python -m harness keep <run 1>
```

This writes `runs/kept.json` and `config/settings.toml` together ([`keep.py`](../../../harness/keep.py#L44-L83)). The last kept run is the parent of every later part. Commit the code, the log and the `runs/` folder (4 min). The reference `.gitignore` of the build repository ignores `runs/`, but your repository must not: the examiner reads your records from GitHub.

If a run has not finished, load the rest from `reference-runs/quillon/` and say so in `results.md`.

| Company | Answer success of run 1 (reference) | Security pass rate of run 1 (reference) |
|---|---|---|
| Quillon | 37% | 81% |
| Juniper Lane | 31% | 77% |
| Saltmarsh | 32% | 88% |

## The tests

```bash
python -m pytest challenges/challenge-1-baseline/part-4-dashboard-and-verdict -q
```

The panels run in Node with a tiny fake page, on fixed run records written inside the test. The test does not read `results.md`, `runs/kept.json` or `LAB-LOG.md`: the examiner checks those. Nothing here reads the reference runs.

- Acceptance, failing on the starter with `AssertionError: panel shows "Panel not built yet", expected a table`: `test_diff_verdict` (10 fixed and 1 broken gives `evidence of improvement`, 4 and 3 gives `inconclusive`, 1 and 9 gives `evidence of harm`, none gives `inconclusive`, and only the flipped cases are listed) and `test_run_tree` (a child sits straight under its parent and the kept run is marked).
- Invariant, passing on the starter: `test_headline` (the shipped headline shows each value with its `n`) and `test_shell_serves_runs` (the shell serves `runs/`).

## If something looks wrong

- **The diff shows 0 questions in both runs.** Your `eligible` test dropped them: a case needs `passed` set as true or false, and `expected_action` of `answer` or `tool`.
- **p is 0.754 with 6 fixed and 4 broken.** That is correct: a 6 to 4 split on ten changed cases is not evidence (a 9 to 1 split would be, with p 0.021).
- **The page and `harness diff` disagree by a case or two.** The page uses the stored verdicts; `harness diff` regrades with the current grader first. The terminal is the version to quote.
