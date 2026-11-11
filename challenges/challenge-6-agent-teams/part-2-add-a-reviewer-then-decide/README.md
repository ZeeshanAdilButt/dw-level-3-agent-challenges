# Lab 6, part 2: add a reviewer, then decide

The packs in this repository are synthetic. A real clinic needs clinical and legal review that this course does not give. The reviewer checks answers against documents only. It never adds medical advice.

## The idea, from zero

A **reviewer** is one more model call at the end of the team. It reads the question, the drafted answer, the document ids the draft cites and the document ids that were delivered. It returns one of two things: pass, or one short instruction for a revision. The core then asks for the revision once, and the revision sees every specialist's documents and tool results. The reviewer is never asked again, so a team cannot loop.

A reviewer can only be worth its cost if it fixes more answers than it breaks. It adds a call to every answer (and two when it asks for a revision), so cost and waiting time rise before quality does. This part measures three designs against one baseline:

1. the single agent, which is the incumbent (the last kept run);
2. the team from part 1;
3. the team with a reviewer.

Every verdict and every cost ratio names its baseline. The reviewer step is compared with the team run. The final choice is compared with the incumbent. A reviewer that beats the team does not make the team better than the single agent.

The decision rule is the one from lab 1: keep a change when the sign test shows evidence of improvement, or when there is no evidence either way and the change makes the agent simpler or cheaper. A team is neither simpler nor cheaper. The budget is at most twice the incumbent's cost per answer. A null result or a loss means you keep the single agent, and the lab is complete when your log explains why.

## What you edit

| File | What you write |
|---|---|
| [`app/agents/reviewer.py`](../../../app/agents/reviewer.py#L9) | `review` |
| [`dashboard/panels/quality-cost.js`](../../../dashboard/panels/quality-cost.js#L8) | the quality against cost and latency panel |
| `predictions/lab6-reviewer.md` | your prediction for the reviewer, before its run |
| `LAB-LOG.md` | the lab 6 entry |

Shipped and not edited: where the core asks for the revision ([`app/agents/__init__.py#L38-L45`](../../../app/agents/__init__.py#L38-L45)), the reviewer prompt (`app/prompts/reviewer.txt`), and the reply rules check, which still runs after everything else in [`_after`](../../../app/core.py#L248).

## Steps

1. **Write the reviewer (15 min).** In [`review`](../../../app/agents/reviewer.py#L8-L9): build one user message with the question, the draft, the cited ids and the delivered ids, make one model call inside a `reviewer` span, find the JSON in the reply, and return `{"verdict": "pass"}` or `{"verdict": "revise", "feedback": ...}` with the feedback cut to 300 characters. A reply that is not usable JSON counts as a pass.
2. **Tests (4 min).** `python -m pytest challenges/challenge-6-agent-teams/part-2-add-a-reviewer-then-decide -q`. Six tests.
3. **Read the team run (6 min).** `python -m harness diff <team-run> <last-kept-run>` regrades both runs from their stored outputs and prints fixed and broken cases, the sign test and the verdict against the incumbent. Note the cost and the slowest-answer time (p95) from the run record.
4. **Smoke check, then the second full run (7 min).** Write `predictions/lab6-reviewer.md` first and commit it. Then:

   ```bash
   python -m harness run --pack <your-pack> --smoke --set topology=router_specialists_reviewer --parent <last-kept-run>
   python -m harness run --pack <your-pack> --set topology=router_specialists_reviewer --parent <last-kept-run>
   ```

   The smoke run is a first look only. Both team runs have the incumbent as parent, so each differs from it by `topology` alone, and the two team runs differ from each other by `topology` alone.
5. **The panel (12 min, an assistant may write this code).** One point per run: cost per answer on one axis, answer success on eligible questions on the other. A second series for the `cross-area` slice. Label each point with its run id, `n` and p95. Give the chart a title that says what it shows. The helpers `L.scatter`, `L.table` and `L.allEvals` are in `dashboard/lib.js`. Each model call in a case carries `hosted_equivalent_usd` in its `usage` row, so the cost of an answer is the sum over those rows.
6. **The three-way table (8 min).** After the wait. Rows: single, team, team with reviewer, each against the incumbent. Columns: answer success on all eligible questions and on the cross-area slice (with `n`), cost per answer and its ratio to the incumbent, p95, verdict. Add one line: `python -m harness diff <reviewer-run> <team-run>`, the reviewer step against the team run.
7. **Decide (5 min).** Apply the rule and the budget. Keep a design with evidence of improvement and a cost of at most twice the single agent's. Over twice, keep it only when your log argues the gain is worth the cost; otherwise revert. With 10 cross-area questions in a pack the verdict is often inconclusive: say so, read the cases that changed in the screen as evidence, and decide on those and the cost limit. To ship a topology: `python -m harness keep <run>`. To stay on the single agent, record each rejected run by name: `python -m harness revert <run>`. Bare `revert` goes back one kept run, so always name the run. Commit `runs/kept.json` and `config/settings.toml`.
8. **Explain and commit (3 min).** In `LAB-LOG.md`: kept or reverted; how far answer success moved against the single agent and on how many questions; the verdict; the reviewer step against the team; the cost ratio against the budget; what you try next.

Finish with `python -m harness gate 6` and read every line.

## Where each number comes from

- **Answer success** and **cross-area success.** Shares of eligible questions answered fully and correctly, from `runs/<run-id>/cases.jsonl`. The cross-area slice has 10 questions on Quillon, so one question moves it by a large step.
- **Cost ratio.** A design's cost per answer divided by the incumbent's. For the reviewer step the divisor is the team run.
- **p95.** The time within which 95 in 100 answers finished: the 95th percentile of the cases' latency. A team's slowest answers sit in the tail.
- **Verdict.** The two-sided exact sign test over cases that were fixed against cases that were broken. Ties are dropped.

## Reference results (measured on the synthetic packs)

| Company | Team: verdict, cost ratio | Team with reviewer: verdict, cost ratio | Reviewer against team: verdict, cost ratio | Calls per answer with reviewer |
|---|---|---|---|---|
| Quillon | evidence of harm, 1.1 | evidence of harm, 1.5 | inconclusive, 1.4 | 3.7 |
| Juniper Lane Clinic | inconclusive, 1.1 | inconclusive, 1.4 | inconclusive, 1.3 | 3.9 |
| Saltmarsh Mutual | inconclusive, 1.1 | inconclusive, 1.5 | inconclusive, 1.4 | 4.0 |

Your own numbers come from your own run records. The gate never compares them with this table.
