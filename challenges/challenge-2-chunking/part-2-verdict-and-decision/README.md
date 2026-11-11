# Challenge 2, part 2: the verdict and the decision

You write the slice panel, read your candidate's verdict and its cost, apply the decision rule, log the decision and mark it with keep or revert. The candidate's full run was started at the end of part 1; it has finished by the time the panel is done. Run every command from the repository root. The packs are synthetic.

## The idea, from zero

One run of the agent tells you how often it was right. It does not tell you whether a change made it better, because the same settings run twice give a few different answers (you measured that in lab 1). So the harness compares a candidate run with its parent, case by case, and counts the questions the change **fixed** (failed before, pass now) and **broke** (passed before, fail now). A two-sided exact **sign test** turns those two counts into a p value: how likely a split this lopsided would be if every flip were a coin toss. Below 0.05 with more fixed than broken, the verdict is evidence of improvement on this set. Below 0.05 with more broken, evidence of harm. Otherwise inconclusive, and an inconclusive result is not "no effect": it is "this set cannot tell".

A verdict is half of a decision. The other half is cost. Chunking changes how many tokens reach the model, so you read **context tokens per answer** against the lab's budget of 25 percent more than the baseline. Where each number comes from: fixed and broken are counts of case ids from the regraded runs ([`compare_verdicts`](../../../harness/diff.py#L80-L100)); p is [`sign_test`](../../../harness/signtest.py#L7-L17); the token change is the candidate's mean delivered tokens minus the baseline's, divided by the baseline's.

## Step 1: the slice panel (20 min)

The overall number can hide where a change helped. A **slice** is the group of questions of one kind. For this lab the two slices that matter are `table` (a fact sits in a table row) and `far-from-heading` (a fact sits far below its heading). A slice has few questions, so every bar must show its `n`: a 9-question slice moves by 11 points when one question flips.

The gap is a block marked `// YOUR TURN` in [`dashboard/panels/recall-slices.js`](../../../dashboard/panels/recall-slices.js#L8). On the starter it draws "Panel not built yet". Write the context fact recall part now (14 min):

- Take the run's question cases ([`L.kindOf`](../../../dashboard/lib.js#L118)) and group them by every slice name they carry.
- For each slice show its `n` and the mean of [`L.factRecallOf`](../../../dashboard/lib.js#L128) (context fact recall) over the cases that have it, as a bar with a real label ([`L.barTable`](../../../dashboard/lib.js#L211-L222) draws a bar inside a table, so the chart is also a table).
- Title the chart with what it shows. A run with no sliced cases says so and draws no 0 percent.
- Follow the interface guidance from lab 1: a table is the layout, one neutral palette, numbers right-aligned.

The reference block also fills recall at 3, recall at 5 and MRR columns; lab 3 uses those, so you may add them now or leave them for then. The panel draws one run. Choose the candidate and then its parent in the page's two selectors to compare the two sets of bars.

Run the test (6 min):

```bash
python -m pytest challenges/challenge-2-chunking/part-2-verdict-and-decision -q
```

## Step 2: read the result (15 min)

1. Open the dashboard (`python -m app`, then `http://localhost:8000/dashboard`) and the diff for the candidate against its parent. Read fixed, broken, unchanged, the p value and the verdict word. In the terminal:

   ```bash
   python -m harness diff <candidate-run> <parent-run>
   ```

   The terminal version regrades both runs with the current grader and prints its version, so quote it. (6 min)
2. Read context tokens per answer for the candidate and its parent, work out the change in percent, and set it against the 25 percent budget. (4 min)
3. Read the `table` and `far-from-heading` slices of both runs with their `n`. Did the slice that the change was meant to help move, and did another slice move the other way? (5 min)

Reference results for the candidate each company's screen chose:

| Company | Candidate | Fixed | Broken | Verdict | Context token change | Decision |
|---|---|---|---|---|---|---|
| Quillon | Fixed 400, overlap 80 | 3 | 1 | inconclusive | 4 percent | revert |
| Juniper Lane | Fixed 400, overlap 80 | 1 | 5 | inconclusive | 1 percent | revert |
| Saltmarsh | Fixed 400, overlap 80 | 4 | 2 | inconclusive | -1 percent | revert |

Saltmarsh's slices for reference: the `table` slice had context fact recall 70% in the baseline and 70% with the candidate over 10 questions; `far-from-heading` had 63% and 63% over 8. These are measured on the synthetic packs; your pack may differ, and a number from one pack is a prediction to test on yours.

## Step 3: decide, log, explain (15 min)

**Apply the rule (4 min).** The rule is printed in part 1 and you apply it in writing. The branches, with made-up (constructed) numbers: 14 fixed, 3 broken, p 0.013, but context tokens up 31 percent against the 25 percent budget and no argument for the extra cost gives **revert**. The same run with a written argument for the extra cost gives **keep**. An inconclusive run keeps only a change that makes the agent cheaper or simpler. Evidence of harm reverts.

**Write the entry (4 min).** In `LAB-LOG.md` add a section headed `Lab 2` with one line each:

```
Claim: ...
Evidence: <the candidate run id> against <its parent run id>, N fixed and M broken, p, verdict
Cost: context tokens up or down X percent against the 25 percent budget
Next: try a different retriever in lab 3
Decision: keep   (or: revert)
```

**Explain the run (5 min).** The same lines answer three questions in your words, not an assistant's. Claim: the candidate chunker is kept or reverted, with the verdict word and the run it was compared with. Evidence: the run ids, the fixed and broken counts and the slice values with their `n`. Cost: the change in context tokens per answer against the budget. Next: try a different retriever.

**Keep or revert, and commit (2 min).** If the decision is keep:

```bash
python -m harness keep <candidate-run>
```

If it is revert:

```bash
python -m harness revert <candidate-run>
```

Each updates `runs/kept.json` and `config/settings.toml` together ([`keep.py`](../../../harness/keep.py#L44-L99)), and your log says which one you ran. Plain `python -m harness revert` with no run id undoes the last kept run, which is not what you want for a candidate you never kept. A well-argued revert completes the lab. `python -m harness gate 2` is run in 2.7, so do not run it yet. Commit.

## The tests

- Acceptance, failing on the starter: `test_slice_panel` (fixed run records give the stated percentages for the two slices, each with its `n`; failure line `AssertionError: panel shows "Panel not built yet", expected bars`) and `test_decision_logged` (the lab 2 entry names claim, evidence run ids that exist in your own `runs/`, cost, next and a decision of keep or revert, and the decision matches what `harness keep` or `harness revert` recorded; failure line `AssertionError: LAB-LOG.md has no lab 2 entry`).
- Invariant, passing on the starter: `test_shell_serves_runs`, `test_the_decision_rule_on_fixed_cases` and `test_the_log_checker_on_fixed_logs`.

## If something looks wrong

- **The slice bars are all 0 percent or all 100 percent.** Check that you average the per-case value; a missing value is `n/a`, not 0.
- **A slice has `n` of 0 for your candidate but not its parent.** The panel reads `ctx.cases` for the selected run; check which run is selected.
- **`harness diff` says NOT COMPARABLE.** The candidate changed more than one setting, or a different model or question set. Start the candidate again with one change.
