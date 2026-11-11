# Lab 6, part 1: router and specialists

The packs in this repository are synthetic. A real clinic needs clinical and legal review that this course does not give.

## The idea, from zero

Your agent today is one loop: it retrieves documents, asks the model, may call tools, and returns an answer. It sees every document type and may use every tool.

A **team** splits that loop. A **specialist** is the same loop with a narrower view: only the documents of one area and only the tools of that area. A **router** is one extra model call that reads the customer's message, picks one area (or two, when the message crosses areas), and writes a short **note** for each specialist. The specialist never sees the chat history, the customer's own message or the principal block. It sees its area prompt, the router's note and its own area's documents.

A team costs more: every extra call adds tokens and waiting. So this part builds the team and starts its full run. Part 2 adds a reviewer and decides, and a lost or null result is a finished lab.

What stays outside the team, on purpose:

- The principal (who is signed in) comes from the core, never from the router's note. The router never sees it.
- The access check, the lab 5 rules layer and the reply rules check run exactly as before, for every specialist call.
- Merging two drafts is shipped, so you can read it in [`app/agents/__init__.py`](../../../app/agents/__init__.py#L15-L46) and not write it.

## What you edit

| File | What you write |
|---|---|
| [`app/agents/router.py`](../../../app/agents/router.py#L12) | `route` and `_clean` |
| [`app/agents/specialists.py`](../../../app/agents/specialists.py#L47-L51) | `run_specialist` |
| `predictions/lab6-teams.md` | your prediction, before any run |
| `config/settings.toml` | not by hand: `harness keep` or `harness revert` changes `topology` for you in part 2 |

Shipped and not edited: the areas, with the document types and tools each may use ([`AREAS`](../../../app/agents/specialists.py#L8-L28)), the prompts in `app/prompts/` (`router.txt`, `specialist.txt`, `merge.txt`), the answer loop in [`app/agents/base.py`](../../../app/agents/base.py#L79-L94), and the core.

## Steps

1. **Prediction (6 min).** Write `predictions/lab6-teams.md`: for the cross-area questions, which design wins, how many points answer success moves (a guess), and the cost ratio. Include your guesses from chapter 6.1. Commit and push before any run.
2. **Read the parent (6 min).** The parent is your last kept run, normally the single agent. Note its run id, its answer success and its cost per answer. One model call per answer is the baseline for calls.
3. **Specialists (18 min).** In [`run_specialist`](../../../app/agents/specialists.py#L47-L53): look up the area's document types and tools ([`area_types`](../../../app/agents/specialists.py#L31-L36)), retrieve with `core.retrieve_turn(turn, types)` so the document filter and the access check run inside retrieval, stop on an authority conflict, build the prompt with [`area_system`](../../../app/agents/specialists.py#L39-L44) and `build_specialist_messages`, which gives the specialist only its area prompt, the router's note and its documents, and run `answer_loop` with the area's tools. The core refuses a tool that is not on the area's list ([`core.py#L140-L141`](../../../app/core.py#L140-L141)).
4. **Router (15 min).** In [`route`](../../../app/agents/router.py#L11-L12): one model call whose system prompt lists the areas, parse a JSON list of `{area, note}`, keep at most two known and distinct areas, and fall back to the first area with an empty note when the reply cannot be used. In [`_clean`](../../../app/agents/router.py#L12): remove the principal's id and account id from each note.
5. **Cross-area check (6 min).** Run the cross-area slice only, then read three traces on the dashboard.

   ```bash
   python -m harness run --pack <your-pack> --slice cross-area --set topology=router_specialists --parent <last-kept-run>
   ```

6. **Tests (4 min).** `python -m pytest challenges/challenge-6-agent-teams/part-1-router-and-specialists -q`. Eight tests. Each one names what a team member must or must not see.
7. **Commit and start the full run (5 min).** The run stops on uncommitted changes. It prints its resolved settings first: only `topology` may differ from the parent.

   ```bash
   python -m harness run --pack <your-pack> --set topology=router_specialists --parent <last-kept-run>
   ```

8. **While it runs (10 min).** Read five more traces from the cross-area run and mark each place where a note lost a fact. Draft what a reviewer should check for part 2.

Write the cross-area table in `results.md` (run id, parent run id, answer success on the slice, `n`) and commit it. Do not run the gate yet: it needs the full run to be complete, so it comes at the end of part 2. The gate checks that every run id in `results.md` is one of your own.

## Where each number comes from

- **Calls per answer.** The count of model calls in an answer: the length of `usage` in each step of `runs/<run-id>/cases.jsonl`, averaged over the answers. A single agent makes about one. A team makes a router call, one call per specialist, and a merge call when two specialists answered.
- **Cost per answer.** The tokens of each call priced with the dated rates in `config/prices.toml`, added up per answer. A local model is free, so the hosted-equivalent rates are what make runs comparable.
- **Answer success on the cross-area slice.** The share of the slice's questions whose reply holds every key fact with a valid citation. The slice has 10 questions on Quillon, so one question is a large step.
- **Waiting time.** The run's `seconds` field in `runs/<run-id>/run.json`.

## Reference results (measured on the synthetic packs)

| Company | Cross-area questions | Calls per answer, team | Cost per answer, single | Wait with GPU (min) | Wait CPU only (min, about, estimated) |
|---|---|---|---|---|---|
| Quillon | 10 | 2.5 | $0.0003 | 18 | 40 |
| Juniper Lane Clinic | 10 | 2.8 | $0.0004 | 27 | 59 |
| Saltmarsh Mutual | 10 | 2.7 | $0.0003 | 26 | 57 |

Your own numbers come from your own run records. The gate never compares them with this table.
