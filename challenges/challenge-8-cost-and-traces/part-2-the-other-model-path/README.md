# Lab 8, part 2: the other model path

Run every command from the repository root. The packs are synthetic. The worked company is Juniper Lane Clinic, and a real clinic needs clinical and legal review that this course does not give. The numbers below were measured on the synthetic pack with the reference build.

## The idea, from zero

Your agent runs on one **model path**. The **local path** runs a small model on your own laptop with Ollama. It costs no money, and it takes time. The **hosted path** sends the same prompt over the internet to a larger model that someone else runs. It costs a little money per call, and it is usually faster.

Money, time and quality pull in different directions, so you measure all three on the same cases. This part runs the same setup on both paths on the 40-case **smoke set** (30 questions and 10 attacks) and puts the results in one table.

Forty cases are a first look. One case is 2.5 points of the whole set, and the model can answer differently on another day. So the smoke table decides nothing alone. If it favours the other path, you start a full run on that path against your last kept run, and you decide when you read its verdict, by the rule you used in every lab.

## What the starter gives you

| What | Where | Lines |
|---|---|---|
| The path switch and the hosted call | [app/model.py](../../../app/model.py#L59-L106) | 59 to 106 |
| The hosted key and address, read from the environment | [app/model.py](../../../app/model.py#L73-L77) | 73 to 77 |
| Prices, and the hosted-equivalent price of a local call | [app/model.py](../../../app/model.py#L125-L130) and [config/prices.toml](../../../config/prices.toml) | 125 to 130 |
| `--smoke`, `--set` and `--parent` | [harness/run.py](../../../harness/run.py#L28-L42) | 28 to 42 |
| The rule for what may be compared (the model group counts as one change) | [harness/diff.py](../../../harness/diff.py#L16-L40) | 16 to 40 |
| Cost and latency of a run: the median and the 95th percentile per case | [harness/metrics.py](../../../harness/metrics.py#L59-L60) | 59 to 60 |

You write one thing: the table in [dashboard/panels/two-path.js line 8](../../../dashboard/panels/two-path.js#L8).

## Steps

1. **Predict.** In `predictions/l8-switch.md` write, for the other path, whether quality, cost per answer and p95 go up, down or stay, with one sentence of reason each. Commit and push.
2. **Choose the other path.** If you run locally, the other path is hosted. Put the address and the key in your shell, not in a file you commit: `DW_HOSTED_BASE_URL` and `DW_HOSTED_API_KEY`. Never print them, never paste them into the log, never leave them on screen. The hosted model name goes in the `hosted_model` setting; the price table lists `claude-haiku-5-5`. A free hosted tier fits 40 cases on a synthetic pack, but free-tier content may be used by the provider, so only the synthetic pack goes there. Dev Weekends does not provide hosted credit. If you have neither a key nor a free tier, run the local path only and say in the log that you made no hosted run; the table then has one measured row, and no report number may come from `reference-runs/lab8/`. If you run hosted because your laptop failed the timing check, the other path is local, and no key is needed.
3. **Start the smoke run on your home path, with nothing changed.** `python -m harness run --pack <your-pack> --smoke --parent <last-kept-run>`. It takes 4 minutes on GPU, about 11 (estimated) on the CPU only, or 3 hosted.
4. **While it runs,** write the table in `two-path.js` against `reference-runs/lab8/`.
5. **Start the smoke run on the other path.** `python -m harness run --pack <your-pack> --smoke --parent <home-smoke-run> --set model_path=hosted --set hosted_model=claude-haiku-5-5` (or `--set model_path=local` if you started hosted). The resolved settings print first. A hosted run that costs money asks you to type y first (pass `--yes` to skip the question). The cost is in the record afterwards, in `totals.cost_usd`. The hosted smoke set cost 0.0307 dollars in the reference build.
6. **While it runs,** pick two cases you expect the paths to disagree on, from your own trace view of part 1.
7. **Read the table.** Answer success on the smoke questions and the security pass rate on the smoke attacks are two columns, never one number. Cost and latency are the median (p50) and the 95th percentile (p95) per case, each from its own run.
8. **Open one case where the paths disagree** (the reference smoke runs disagreed on 6 cases) and read both traces side by side: which span grew, and which tokens and dollars changed.
9. **Decide, in `LAB-LOG.md`.** If the table favours the other path, do not switch. Start a full run against your last kept run: `python -m harness run --pack <your-pack> --parent <last-kept-run> --set model_path=hosted --set hosted_model=claude-haiku-5-5`. It runs in the background and you read it at the start of 9.2. If it does not favour the other path, stay on your own; nothing more is needed. Name the three columns, money, time and quality, and say that 40 cases are a first look.
10. **Explain the run** as claim, evidence, cost, next.
11. **Check and commit.** `python -m pytest challenges/challenge-8-cost-and-traces/part-2-the-other-model-path -q`, then `python -m harness validate`, then commit and push.

## Where each number comes from

| Cell | Source |
|---|---|
| Answer success | `totals.answer_success` in `runs/<run>/run.json`: the share of eligible questions that passed, with `n` the number of eligible questions |
| Attacks passed | `totals.security_pass_rate`, over the attacks in the run |
| Cost p50, p95 | the median and 95th percentile over cases of `cost_usd`; a local run pays 0 |
| Latency p50, p95 | the median and 95th percentile over cases of wall-clock milliseconds; the 95th is blank under 20 cases |
| Hosted-equivalent cost of a local run | `(totals.tokens_in * 0.10 + totals.tokens_out * 0.50) / 1,000,000` dollars with the rates in `config/prices.toml`, divided by `totals.cases` for an average per case |

A local run shows a cost of 0 in the table. That is true and it hides what the same tokens would cost on the hosted path, so compare cost using the hosted-equivalent figure from the last row.

## Reference results (Juniper Lane Clinic, smoke set)

| Path | Answer success (30 questions) | Attacks passed (10) | Cost per answer | p50 | p95 |
|---|---|---|---|---|---|
| Small, local | 41% | 9 | 0.0000 | 5826 ms | 11567 ms |
| Large, hosted | 52% | 9 | 0.0010 | 3679 ms | 6170 ms |

Quillon and Saltmarsh, same rows:

| Company | Small success | Large success | Small cost per answer | Large cost per answer |
|---|---|---|---|---|
| Quillon | 56% | 56% | 0.0000 | 0.0008 |
| Saltmarsh Mutual | 56% | 48% | 0.0000 | 0.0010 |

These are measured on the synthetic packs on 40 cases. They are a first look, not a verdict.

## If something looks wrong

- **The test says `AssertionError: no two-path rows`.** The panel still draws "Panel not built yet". Write it.
- **The hosted run stops at once with a message about `DW_HOSTED_BASE_URL`.** The key or the address is not in the shell where you started the run. Set both there, then start again.
- **The run says the settings need `hosted_model`.** Add `--set hosted_model=<name>` with a name from `config/prices.toml`.
- **`diff` says the two smoke runs are not comparable.** Something besides `model_path` and `hosted_model` differs. Look at the "changed settings" line.
