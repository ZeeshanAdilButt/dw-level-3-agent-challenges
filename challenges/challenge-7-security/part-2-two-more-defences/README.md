# Lab 7, part 2: two more defences

The packs in this repository are synthetic. A real clinic needs clinical and legal review that this course does not give.

## The idea, from zero

Part 1 kept internal text out of the prompt. Two attacks still get through it:

- A **public** page that carries orders ("ignore your rules and reveal ..."). The access check lets it in, because the page is public. **Marking** wraps each retrieved chunk in a labelled block that says it is untrusted, so the model can tell data from orders. You wrote it in part 1. It lowers the risk and does not remove it.
- A reply that leaks something anyway: the system prompt, a personal detail, or text from a document the principal may not see. The **leak check** is code that compares the reply, before it leaves, with three things: runs of words copied from the system prompt, the shipped PII patterns, and the text of items the principal may not see. A blocked reply is replaced by one short fixed sentence. It is a **detector**, not a guarantee: a leak in new words can pass it.

Each defence is one more step in a stack. Each run's parent is the last kept run, so every stack you keep is a stack you measured. You keep a defence by the lab's decision rule on the security endpoint: evidence of improvement, or no evidence either way and the agent is simpler. Otherwise you revert it and say which attacks you now give up.

Your agent code holds no confidential literal. It may not contain a canary (a planted value that makes a leak visible), a gold answer or a read of `eval/` or `runs/`. The leak check finds hidden text by searching the index without the access check, never by knowing what to look for.

Eight attacks per family is a small set. One attack moves a family by 12.5 points.

## What you edit

| File | What you write |
|---|---|
| [`app/security/output_check.py`](../../../app/security/output_check.py#L28-L35) | `leak_check`. The file [`app/security/leak_check.py`](../../../app/security/leak_check.py) only re-exports it under the lab's name. |
| [`dashboard/panels/security.js`](../../../dashboard/panels/security.js#L8) | the over-refusal count beside the per-family table |
| `predictions/l7-leak.md` | your prediction, written by yourself |
| `LAB-LOG.md` | the lab 7 entry, with the paragraph on what 48 attacks cannot show |

Shipped and not edited: the call in the core ([`core.py#L248`](../../../app/core.py#L248)) that blocks a reply and removes its citations, the call that runs `leak_check` on every handoff note, including the model's own `hand_off` note ([`core.py#L248`](../../../app/core.py#L248)), the word-run helpers ([`output_check.py#L13-L25`](../../../app/security/output_check.py#L13-L25)) and the PII patterns. Lab 5's reply rules check stays in `app/rules/`.

## Steps (70 min)

1. **Read the marking run (6 min).** The per-family table, then `python -m harness diff <marking-run> <access-run>`: all 48 attacks, fixed against broken, baseline named. Then the over-refusals out of the answerable questions.
2. **Decide marking (6 min).** Lab 7's cost limit is at most 5 more refused or handed-off answerable questions in every 100 than the last kept run. Over the limit, revert. Within it, keep marking on evidence of improvement, or when there is no evidence either way and the agent is cheaper or simpler. An inconclusive verdict with a more complex agent means revert, and you say which attacks you now give up. Evidence of harm means revert. `python -m harness keep <marking-run>` or `python -m harness revert <marking-run>`. The run stays in your table either way. Say the over-refusal cost in plain words: which answerable questions were refused, and what a customer lost.
3. **Write the leak check (14 min).** In [`leak_check`](../../../app/security/output_check.py#L34-L36). Given the reply, the system prompt, the principal, the index and the text the principal already holds (the person's own records, the receipts of their own tool calls and their earlier replies, not the message they type and never the model's text):
   - if the reply holds a run of 7 or more words copied from the system prompt, add `system-prompt`;
   - for the first PII pattern found whose value is not in the principal's own text, add `pii:<name>`;
   - split the reply into sentences of at least 5 words; for each, search the index without the access check, and when a hidden item holds a 7-word run of that sentence and no visible item does, add `hidden-text:<doc id>`. Then run the same search on the whole reply as one text, so a run of 7 words that crosses two sentences is found too. The 7-word rule stays.

   Known limit: the 7-word check does not catch short confidential facts or codes.

   Return the reasons (an empty list means clean). A handoff note goes through the same check, so the note path is tested here too.
4. **Tests (4 min).** `python -m pytest challenges/challenge-7-security/part-2-two-more-defences/test_leak_check.py -q`. Eight tests. They use a fixture index and an invented canary, and the last one is the handoff note test that used to sit in part 1. On a built starter 6 of the 8 fail with an `AssertionError` such as `assert 'system-prompt' in []`, because the stub returns no reasons. The two tests that expect a clean reply pass.
5. **Prediction (3 min).** Write `predictions/l7-leak.md` yourself. Commit and push.
6. **Start the third run (2 min).** Name the defences you kept, then the new one. The printed settings must show that one addition.

   ```bash
   python -m harness run --pack <your-pack> --parent <last-kept-run> --set defences=<the kept defences>,output_check
   ```

7. **While it runs (11 min).** Add the over-refusal count beside the per-family table in `security.js`, and draft the "what 48 attacks cannot show" paragraph.
8. **Read the stacked table (5 min).** Save it in `LAB-LOG.md` and in this part's `results.md`. One row per run (baseline, access, marking, leak), one column per family, each cell a pass rate with `n` of 8, and the over-refusal count out of the answerable questions.
9. **Write "what 48 attacks cannot show" (4 min).** In your own words: 8 attacks per family is a small set; a family at 8 of 8 means these 8 phrasings failed, not that the family is closed; string checks are limited detectors; one run is one draw from a model that can answer differently; a defence can pass attacks by refusing almost everything, which is why over-refusals are counted; the examiner sends phrasings you have not seen.
10. **Decide the leak check (6 min).** Same rule and cost limit, verdict named against the last kept run. It is aimed at system-prompt: keep it on evidence of improvement, and revert it when the verdict is inconclusive and it makes the agent more complex. `python -m harness keep <leak-run>` or `python -m harness revert <leak-run>`, which leaves the last kept stack, a stack you already ran. If you reverted marking in step 2, the leak run measured access plus the leak check, and that is the stack you keep or drop. If a defence refuses answerable questions, you may tune it once (one more run, one code change) and log what you tried. Say if a defence did not move the family it targets.
11. **Explain the run (6 min).** In `LAB-LOG.md`: claim, evidence, cost, next.
12. **Validate and commit (3 min).** Run both part tests, then `python -m harness validate`, then `python -m harness gate 7`. Commit the log and the run records and push.

## Where each number comes from

- **Fixed and broken (security).** Attacks that failed in the parent and pass in the candidate, and the reverse, regraded from stored outputs by the same grader ([`harness/diff.py`](../../../harness/diff.py#L43-L81)). Ties are dropped, and the sign test uses fixed against broken only.
- **Family pass rate with `n`.** Attacks passed over the family's attacks. `n` is 8.
- **Over-refusals.** Answerable questions that were refused or handed off, over all answerable questions. A blocked reply counts when the question was answerable.

## Reference results (measured on the synthetic packs)

Quillon, whose price rule from lab 5 already checks replies:

| Family (n is 8) | Marking run | Leak run |
|---|---|---|
| doc-injection | 8 of 8 | 8 of 8 |
| system-prompt | 8 of 8 | 8 of 8 |
| internal-content | 8 of 8 | 8 of 8 |
| domain-harm | 6 of 8 | 6 of 8 |

| Run | Fixed | Broken | Over-refusals out of 81 |
|---|---|---|---|
| Marking against access | 2 | 0 | 6 |
| Leak check against the last kept run | 1 | 0 | 6 |

A full run takes 13 minutes with a GPU and about 29 minutes (estimated) on the CPU only.

Your own numbers come from your own run records. The gate never compares them with this table.
