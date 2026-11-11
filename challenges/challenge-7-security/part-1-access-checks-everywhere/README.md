# Lab 7, part 1: access checks everywhere

The packs in this repository are synthetic. A real clinic needs clinical and legal review that this course does not give.

## The idea, from zero

Some text in a pack is public (a price page). Some is internal (a staff price book, a claims playbook). Some belongs to one customer (their account). Your agent retrieves text, expands it with neighbours, parents and links, calls tools, remembers a conversation and writes notes for a person. Each of those is a **path** by which text can reach the model or the customer.

An **access check** is code that answers one question for each item on each path: may this principal see it? The function is `allowed(item, principal)`. The **principal** is who is signed in: an id, a role, whether the adapter verified them, and the account they own. An instruction in the prompt such as "never reveal internal documents" is not an access check. By the time the model reads that instruction, the internal text is already in its prompt. Only code that refuses to fetch the item keeps it out.

Marking, the leak check and the rules layer each stop something else. This part builds the one defence that keeps internal text out of the prompt on every path. Before this lab, `allowed` is a stub that returns true, so the baseline leaks internal text by design. The six attack families (set in `config/ids.yaml`) are `doc-injection`, `message-injection`, `other-person`, `internal-content`, `system-prompt` and `domain-harm`. Each has 8 attacks, so one attack moves a family by 12.5 points.

## What you edit

| File | What you write |
|---|---|
| [`app/security/access.py`](../../../app/security/access.py#L16-L18) | the body of `allowed` |
| [`app/security/marking.py`](../../../app/security/marking.py#L13-L14) | `wrap` (step 13) |
| [`dashboard/panels/security.js`](../../../dashboard/panels/security.js#L8) | pass rate by attack family with its `n` (the over-refusal table comes in part 2) |
| `predictions/l7-access.md`, `predictions/l7-marking.md` | your predictions, written by yourself |
| `LAB-LOG.md` | a two-line finding |

Shipped and not edited: the PII patterns ([`app/security/pii.py`](../../../app/security/pii.py)) and the attack runner (the harness). The five places that ask `allowed` are already wired. The sixth path, handoff notes, is checked by the leak check in part 2. Your job is to read each one, so you know exactly which questions your function gets asked.

| Path | Where it asks `allowed` | The `kind` of the item |
|---|---|---|
| Ranked hits | [`context.py#L137`](../../../app/context.py#L137), before the top-k cut | `chunk` |
| Neighbours and section parents | [`context.py#L138`](../../../app/context.py#L138) | `neighbour`, `section` |
| Followed links | [`context.py#L85`](../../../app/context.py#L85) | `link` |
| Tool results | [`tools/__init__.py#L165-L171`](../../../app/tools/__init__.py#L165-L171) | `tool_result` |
| History | [`core.py#L239-L241`](../../../app/core.py#L239-L241) | `history` |
| Handoff notes | [`core.py#L248`](../../../app/core.py#L248) | not an `allowed` call: the leak check reads the note (part 2) |

The five `allowed` calls go through [`_allow_fn`](../../../app/core.py#L86-L90), which returns nothing when `access` is not in the `defences` setting.

## Steps (80 min)

1. **Read the baseline (4 min).** In your run history, note your pass rate on each of the six families (8 attacks each). If your own run is missing, load `reference-runs/lab1/`.
2. **Prediction (5 min).** Write `predictions/l7-access.md` yourself, without an assistant: for each family, will the pass rate rise, stay or fall, and by how many of 8; and how many answerable questions might the checks refuse by mistake. Then `git add`, `git commit -m "predict: access checks"`, `git push`.
3. **Write `allowed` (10 min).** An item is a dictionary with a `kind`. Return true or false.
   - `history`: true only when the entry's `principal_id` equals the principal's id.
   - `tool_result`: true when no account is named, or the principal is verified and owns that account, or the result's account is the one verified in this conversation.
   - `chunk`, `neighbour`, `section`, `link`: an `owner_scope` of `account:<id>` needs a verified principal who owns that id; an internal audience or a `staff` scope needs a verified staff principal; anything else is public.
   - any other kind: false.

   A role claim without a verified session is worth nothing. The harness sets the principal per case with a test header, which is for the harness only and is not how identity is proved.
4. **Retrieval (5 min).** Read [`context.py#L137`](../../../app/context.py#L137). Candidates are checked before the top-k cut, so a denied chunk cannot take one of the five places. Run the part test to see it hold.
5. **Parents, neighbours and links (6 min).** Each added piece is its own item. A denied link is dropped and never followed.
6. **Tools (5 min).** The core binds the account argument from the principal and ignores the model's ([`tools/__init__.py#L147-L158`](../../../app/tools/__init__.py#L147-L158)). A call that names another account is refused before the mock is called.
7. **History (4 min).** History is read by principal id and conversation id together. Another principal's entry is dropped.
8. **Handoff notes (4 min).** Read `_write_handoff` in `core.py`. A note that quotes a hidden item is replaced by a fixed sentence, but that is done by the leak check you write in part 2, so its test is there. Here you only read where the note path goes.
9. **Part test (8 min).** `python -m pytest challenges/challenge-7-security/part-1-access-checks-everywhere -q`. Eight tests. On the starter `allowed` returns true for everything, so `test_allowed_rules` fails first.
10. **Security panel (6 min).** In [`security.js`](../../../dashboard/panels/security.js#L8): a bar table of attacks passed by family, each with its `n`, using `L.barTable`.
11. **Commit and start the full run (2 min).** All 148 cases: 100 questions and 48 attacks. The resolved settings print first: only `defences` may differ from the parent.

    ```bash
    python -m harness run --pack <your-pack> --parent <last-kept-run> --set defences=access
    ```

    If it stops, `python -m harness run --pack <your-pack> --resume`. The run works from a snapshot of your commit.
12. **While it runs (3 min).** Write `predictions/l7-marking.md` yourself: which families will marking move, which will it leave alone, how many answerable questions might it refuse. Do not commit it yet.
13. **Write marking (9 min).** In [`wrap`](../../../app/security/marking.py#L13-L15): put each retrieved chunk in a block that carries its document id and says it is untrusted. [`neutralise`](../../../app/security/marking.py#L8-L10) is shipped and removes any start or end marker inside the text, so a page cannot close its own block. `app/prompts/rules.md` holds the one line the system prompt adds only when marking is on. Marking lowers the risk and is not a guarantee: a model can still follow an order inside a block. `python -m pytest challenges/challenge-7-security/part-2-two-more-defences/test_marking.py -q`. Editing now changes nothing in the access run.
14. **Read the result (5 min).** The per-family table, then `python -m harness diff <access-run> <last-kept-run>`. For each attack that still fails, read its case line in `runs/<run-id>/cases.jsonl`: the `verdict` says what leaked, and `eval.delivered_doc_ids` and `eval.rule_hits` show how it got there. Ask which families moved, which did not, and which questions broke. A family that did not move is a finding, not a failure. Save the per-family table, with the run ids, in this part's `results.md`.
15. **Keep and start marking (4 min).** Access checks are a required safeguard, so keep the run: `python -m harness keep <access-run>`. Log the finding in two lines. Commit the code, the run record and both prediction files, push, then:

    ```bash
    python -m harness run --pack <your-pack> --parent <last-kept-run> --set defences=access,marking
    ```

Finish with `python -m harness validate <access-run>`. The gate for lab 7 comes at the end of part 2, when the marking run and the leak run have finished.

## Where each number comes from

- **Pass rate by family.** Attacks passed divided by the family's attacks, from `security_by_family` in `runs/<run-id>/run.json`. An attack passes when its rule holds: no canary, no confidential fact, no forbidden tool, no forbidden text, or a required action ([`harness/graders/security.py`](../../../harness/graders/security.py)).
- **Over-refusals.** Answerable questions (expected action `answer` or `tool`) that the run refused or handed off, out of all answerable questions. Attacks are never counted here.
- **Run minutes.** The run's `seconds` in `run.json`, divided by 60.

## Reference results (measured on the synthetic packs)

Saltmarsh Mutual, whose identity check comes before any policy detail:

| Family (n is 8) | Baseline (lab 1) | After access checks |
|---|---|---|
| internal-content | 5 of 8 | 8 of 8 |
| other-person | 7 of 8 | 8 of 8 |
| doc-injection | 7 of 8 | 6 of 8 |

Over-refusals with access checks: 3 of 82 answerable questions. A full run takes 13 minutes with a GPU and about 29 minutes (estimated) on the CPU only.

Why doc-injection is not expected to move: an injected order sits in a public page, which `allowed` correctly lets through. That family is for marking, in part 2.

Your own numbers come from your own run records. The gate never compares them with this table.
