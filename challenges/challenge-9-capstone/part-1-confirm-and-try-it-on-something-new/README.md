# Capstone, part 1: confirm the best setup, and try it on something new

Run every command from the repository root. The packs are synthetic. The worked company is Saltmarsh Mutual. The numbers below were measured on the synthetic pack with the reference build.

## The idea, from zero

Your best run might have been a lucky one. The model does not answer the same way every time, so one run is one draw. You already know this from the noise floor in lab 1.

A **confirmation** runs the best setup three times and the baseline setup three times, with no reused replies. For each case, the majority of the three runs decides: a case counts as passed on a side when at least two of its three runs passed it. A case marked must-pass is the exception. It counts as passed only if all three runs passed it, so a must-pass failure in any run is never hidden by the majority, and the confirmation lists it.

The baseline runs again on **today's code**, with `--from-run`. That restores the old settings but not the old code. Otherwise the best side would run new code and the baseline side old code, and the comparison would have two differences.

The three confirmation runs use the same public questions your choices in labs 2 to 8 were made on. They show that the result is stable. They do not show that it carries over to questions you have not seen. That is why the checker has an unseen set, and why you write ten questions of your own here, in a separate copy of the pack, about a memo the corpus never had.

## What the starter gives you

| What | Where | Lines |
|---|---|---|
| `--repeat` (fresh runs, cache off) and `--from-run` (old settings, new code) | [harness/run.py](../../../harness/run.py#L28-L42) | 28 to 42 |
| One verdict per case from several runs, must-pass failures kept | [harness/confirm.py](../../../harness/confirm.py#L23-L59) | 23 to 59 |
| The confirmation file and what it prints | [harness/confirm.py](../../../harness/confirm.py#L83-L129) | 83 to 129 |
| What a confirmation file must hold | [harness/schema.py](../../../harness/schema.py#L65-L72) | 65 to 72 |
| What a pack copy must satisfy | [harness/pack_check.py](../../../harness/pack_check.py#L32-L136) | 32 to 136 |

You write no Python here. You edit `packs/<your-pack>-mine/`, `predictions/l9-confirm.md` and `LAB-LOG.md`.

## Steps

Sitting 1 is steps 1 to 7. Sitting 2 is steps 8 to 11 and starts when the six runs have ended, which may be the next day. Leave the laptop plugged in and awake while the runs go.

1. **Settle the best setup.** `config/settings.toml` must hold the setup you decided in labs 2 to 8, and `git status` must be clean. If you started a full run for a model switch in 8.5, read it first and keep it (`python -m harness keep <run>`) or turn it down (`python -m harness revert <run>`). Do not change `packs/<your-pack>/` or any code after this point.
2. **Predict.** In `predictions/l9-confirm.md`: the best setup's success against the baseline, how many cases will flip between the three runs, and whether any must-pass case will fail. Commit and push.
3. **Make the separate copy.** Copy `packs/<your-pack>/` to `packs/<your-pack>-mine/`. All your new work happens in the copy.
4. **Write the memo.** One page of plain business English that adds one rule the corpus does not have. Allowed topics: how a trial or first period works; how a customer asks for a credit or a correction, and by when; who may approve an exception. Search the corpus first so your rule is really new. Fill the front matter: `doc_id`, `title`, `audience`, `owner_scope`, `authority`, `version_chain`, `effective_from`, `supersedes`, `links`. The file name is the `doc_id` plus `.md`, in `corpus/`. You may use an assistant for the wording. The facts in it are yours.
5. **Write ten questions** in `eval/questions.jsonl` of the copy, in the same shape as the public ones, with key facts tied to their entity, gold sources and spans. At least two need the memo, at least one needs a tool, at least one must go to a person. Do not look at the agent's replies while you write. Remove `eval/attacks.jsonl` and `eval/smoke.jsonl` from the copy, or leave them empty, so a run on the copy holds only your ten.
6. **Check and commit the copy.** `python -m harness pack-check <your-pack>-mine`, then `python -m pytest challenges/challenge-9-capstone/part-1-confirm-and-try-it-on-something-new -q` (the pack tests pass; the confirmation test fails until step 8, and that is expected now), then `git add packs/<your-pack>-mine`, commit and push. A run refuses a tree with uncommitted files, so the copy is committed before the runs.
7. **Start the six runs.** First the best setup three times, then the baseline three times on today's code, joined with `&&` so the second starts by itself. The baseline run id is your lab 1 run, in the run history. Sitting 1 ends here:

   ```bash
   python -m harness run --pack <your-pack> --from-run <last-kept-run> --repeat 3 && python -m harness run --pack <your-pack> --from-run <baseline-run> --repeat 3
   ```

   Each run works from a snapshot of the committed tree and refuses to start if anything outside `runs/` and `.cache/` is uncommitted. Change nothing in the repository until both commands finish: the baseline starts hours later and would stop with status 3, and a commit in between makes the two sides run different code. The six runs take 112 minutes on GPU, and about 2.2 times as long on the CPU only (an estimate from the measured time per model call). Most of that waiting is still ahead when sitting 1 ends. With a team topology a CPU-only wait can be hours.
8. **Confirm.** When the six runs have ended: `python -m harness confirm --best <three best run ids> --baseline <three baseline run ids>`. It writes `runs/confirm-<id>.json` and prints, for each side, answer success by majority, security and must-pass failures, then the best side against the baseline: cases fixed, cases broken and the sign test. The file also holds the cost, latency, calls and tokens of each side, pooled over its three runs. Note how many cases flipped between the three best runs.
9. **Run your ten.** `python -m harness run --pack <your-pack>-mine --no-cache --parent <last-kept-run>`. Ten questions take about 1 minute on GPU and about 2 on the CPU only.
10. **Compare and write the gap** in `LAB-LOG.md`: the own-ten score against the public score (the best side's majority). Ten questions are a rough guide, because each moves the score by 10 points. Say that the public questions are the ones your choices were tuned on, and that the baseline was rerun on today's code.
11. **Test, commit and push.** Run the part test again; every test must pass now. Then commit and push the six run records, the confirmation file, the pack copy, the prediction and the log.

## Where each number comes from

| Number | Source |
|---|---|
| Answer success of a side | `best.answer_success` or `baseline.answer_success` in `runs/confirm-<id>.json`: the share of eligible questions that the majority passed, with `den` the eligible questions |
| Each run's own answer success | `best.per_run_answer_success` in the same file |
| Flips between runs | cases whose pass or fail differs between the three runs of one side |
| Must-pass failures seen | `must_pass_failures_seen` in the same file, with the run ids that failed |
| Own-ten score | `totals.answer_success` in the run record of step 9 |
| The gap | public score minus own-ten score, in percentage points; a guess from ten questions |

## Reference results (Saltmarsh Mutual)

Best setup 39% against baseline 33%, by majority of three runs per side, the baseline rerun on today's code. 5 cases flipped between the three best runs. Must-pass cases failed in any run: 1. The reference build has no own ten, so there is no reference gap.

| Company | Best | Baseline |
|---|---|---|
| Quillon | 42% | 37% |
| Juniper Lane Clinic | 35% | 33% |
| Saltmarsh Mutual | 39% | 33% |

These are measured on the synthetic packs. A prediction for your own pack is something to test, not to assume.

## If something looks wrong

- **`confirm` says one side's runs have different settings.** The three runs of a side must be one configuration. Check you passed three ids from the same `--repeat 3` command.
- **`confirm` prints a note that the baseline used different code.** You started the baseline with an old run's code. Run it again with `--from-run`, on today's commit.
- **`confirm` refuses with an error before it writes anything.** Each side needs at least 3 complete full runs. The runs of a side need a distinct `seed_salt`, which `--repeat` sets, so a run started without it or a `--url` run is refused. Smoke and slice runs are refused, and so are runs of a different pack or question set. The best side and the baseline may differ in several settings, but each side must be one configuration. The message names the run.
- **The test says `FileNotFoundError: runs/confirm-*.json`.** Step 8 is not done yet.
- **A must-pass case shows as failed although two runs passed it.** That is the rule working. Open the run that failed it and read why.
