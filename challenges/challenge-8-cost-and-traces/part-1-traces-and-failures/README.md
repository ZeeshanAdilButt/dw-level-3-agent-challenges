# Lab 8, part 1: traces and failures by type

Run every command from the repository root. The numbers below are measured on the synthetic Quillon pack with the reference build. Your run prints your own.

## The idea, from zero

A slow answer is not one thing. The agent looks up chunks, may call a rule, may call a classifier, calls the model, may check the reply. Which step took the time? You cannot tell from the total.

A **span** is a stopwatch with a name and a parent. It records when a step started and when it ended. A step that runs inside another step is its child. The parent's time includes its children, so you never add a child to its parent. A **trace** is all the spans of one answer, drawn as nested bars.

A span stores **tokens** (how much text went in and out of a model). It does not store dollars. Dollars are computed later, from the tokens and the price of the model that call used, so one price table decides every cost.

A **failure type** is the one label a failed case gets, so you can count why cases fail. There are twelve types and they are checked in a fixed order. The first one that matches wins, so a case that leaks and also states a wrong fact is counted once, as `leak`. The order is `FAILURE_ORDER` in `harness/graders/case.py`: `tool_error` is 7, `over_refusal` is 8 and `wrong_action` is 9. A handoff with no note and a clarify that failed are `wrong_action`, and so is a tool that was never called, because no call failed.

## What the starter gives you

| What | Where | Lines |
|---|---|---|
| The root span of every answer, `handle` | [app/core.py](../../../app/core.py#L241-L242) | 249 to 250 |
| One `model` span per model call, with tokens and the model name | [app/model.py](../../../app/model.py#L59-L69) | 59 to 69 |
| The tracer: ids, parent ids, inclusive times | [app/trace.py](../../../app/trace.py#L28-L39) | 28 to 39 |
| Dollars of one call from the price table | [app/model.py](../../../app/model.py#L125-L130) | 125 to 130 |
| The price table, with the date it was written | [config/prices.toml](../../../config/prices.toml) | all |
| The call sites that ask for a step span | [app/core.py](../../../app/core.py#L243) | 263, 268, 314, 338 |
| Retrieve, expand and assemble spans | [app/context.py](../../../app/context.py#L137) | 194, 206, 226 |
| The twelve failure types and their order | [harness/graders/case.py](../../../harness/graders/case.py#L23-L24) | 23 to 24 |
| The function that picks a case's type | [harness/graders/case.py](../../../harness/graders/case.py#L235) | 235 to 269 |
| The slowest step of a run | [harness/metrics.py](../../../harness/metrics.py#L68) | 68 to 85 |

## Steps

1. **Predict.** In `predictions/l8-trace.md` write which step will be slowest, which will cost the most, and which failure type will be most common. Commit and push before you run anything.
2. **Write the span.** Open [app/core.py lines 95 to 97](../../../app/core.py#L95-L97). `Agent.span(turn, name, force=False, **attrs)` must return a span for the structural steps always (the router, the specialists and the reviewer pass `force=True`) and for every other step only when `trace_steps` is `on`. When it is off, it must return something that does nothing, so the code path is the same. The five call sites already exist. Run `python -m pytest challenges/challenge-8-cost-and-traces/part-1-traces-and-failures/test_traces.py -q`.
3. **Look at the stored spans.** After a run with `trace_steps=on`, each case line in `runs/<run>/cases.jsonl` holds its spans under `steps[].eval.spans`, next to the model spans.
4. **Read the failure types.** Read `failure_type` ([lines 263 to 300](../../../harness/graders/case.py#L263-L300)) and write on a sheet, for three of your own failed cases, the type you expect. Then run `python -m pytest challenges/challenge-8-cost-and-traces/part-1-traces-and-failures/test_failure_types.py -q`. The test builds twelve cases by hand, one per type, and a case that leaks and states a wrong fact.
5. **Prove tracing changes nothing.** `python -m pytest challenges/challenge-8-cost-and-traces/part-1-traces-and-failures/test_trace_neutral.py -q`. The stub model gives fixed replies, so the same cases must give identical replies, citations, actions and mock state with tracing off and on. A live run cannot prove this, because the live model varies a little between runs.
6. **Commit, then start the run.** `python -m harness run --pack <your-pack> --parent <last-kept-run> --set trace_steps=on`. Its one change is `trace_steps = on`. On the reference laptop it takes 13 minutes with the GPU and about 29 minutes (estimated) on the CPU only. The run works from a snapshot, so you can edit while it runs.
7. **Build the trace view** in [dashboard/panels/trace.js](../../../dashboard/panels/trace.js#L8) against `reference-runs/lab8/` while the run goes. One case as nested rows with start, inclusive duration, a bar, model, tokens, dollars and hosted-equivalent dollars, then the steps across all cases, slowest first. Test: `test_traces.py` draws the panel on three fixed spans.
8. **Describe the diff, then keep.** `python -m harness diff <run> <last-kept-run>`. Read it as a description of ordinary variation, beside your noise floor (the reference floor was 0 flipped cases). The neutral test is the proof, not these flips. Then `python -m harness keep <run>`. Tracing is required by this lab, so it is kept without a gain.
9. **Build the failures panel** in [dashboard/panels/failures.js](../../../dashboard/panels/failures.js#L8): one row per type in checking order, each failed case counted once, the number out of all failed cases. Test: `test_failure_types.py`.
10. **Name the slowest step** in `LAB-LOG.md`, from your trace view or from `metrics.slowest_step` in `runs/<run>/run.json`, and compare it with your prediction.
11. **Commit and push** the code, the run record and the log.

## Where each number comes from

| Number | Source |
|---|---|
| Span start and end | `Tracer.now_ms()`, milliseconds since the answer began |
| Span duration | end minus start, inclusive of children |
| Latency of a case | the root span's end minus its start, the value in `Reply.latency_ms` |
| Tokens of a span | the `usage` of the model call, or a count of the text for the stub |
| Dollars of a call | `(tokens_in * input + tokens_out * output) / 1,000,000` with the rates of that call's own model in `config/prices.toml` |
| Slowest step | the direct child of a root span with the greatest median inclusive duration, `slowest_step` in `harness/metrics.py` |
| Failure counts | `metrics.failures_by_type` in `run.json`, one count per type, and `total_failed` |

## Reference results (Quillon, 13 minutes on GPU)

The tracing run changed one setting, `trace_steps`. Its slowest step was model, with a median of 6006 ms. Its most common failure type was retrieval miss, 24 of 63 failed cases.

| Company | Slowest step | Most common failure type | Failed cases |
|---|---|---|---|
| Quillon | model | retrieval miss | 63 |
| Juniper Lane Clinic | model | retrieval miss | 75 |
| Saltmarsh Mutual | model | retrieval miss | 72 |

These are measured on the synthetic packs. Your agent may differ, which is the point of tracing it.

## If something looks wrong

- **The span test fails with `AssertionError: no span for ('rules', None)`.** You have not written `Agent.span` yet, so it records nothing.
- **No step spans in `cases.jsonl`.** The run was made with `trace_steps` off. Spans of the model and the root always record.
- **A child sticks out of its parent.** A span was opened and closed in the wrong order. Open and close spans with `with`, never by hand.
- **The failures panel does not add up.** Count only cases with `passed` equal to false, and count each once under its `failure_type`.
