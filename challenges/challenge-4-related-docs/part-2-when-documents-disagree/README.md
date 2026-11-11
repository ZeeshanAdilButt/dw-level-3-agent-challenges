# Challenge 4, part 2: when documents disagree

You read the verdict of the context run you started in part 1 and decide whether to keep it. Then you write the rule that says which of two documents to trust when they disagree, screen it, start a second full run on top of the kept context run, and explain both. The worked company is Saltmarsh Mutual. The packs are synthetic. Run every command from the repository root.

50 work minutes plus waiting on the reference laptop. Steps 1 and 2 come before you read the context run, so it is normally finished by step 4 (13 minutes with a GPU, about 29 minutes (estimated) CPU only, for Saltmarsh). Step 6 starts the authority run. It makes extra calls, so it takes longer: 12 minutes with a GPU and 26 minutes CPU only. Step 7 uses part of that wait. No step needs the run before step 8.

## The idea, from zero

Retrieval can bring back two documents that give different answers to one question. An older brochure says a flood is covered. The current policy wording says it is excluded (doc-brochure-2025 and doc-hw-c45x-flood-excl in the reference pack). A model given both will pick one, and it has no way to know which one a court or an ombudsman would pick. A fixed rule can.

The rule has four parts, in this order:

1. **Applicability.** A document that is not in force on the evaluation date (2026-11-01, fixed so every run is comparable), or that is about another product or customer group than the one the question is about, takes no part. It is not "older" or "lower". It is not a candidate.
2. **Conflict groups.** The documents that remain are grouped by topic, the rule they state. One document can state several rules: a price table states every plan's price. Two documents of different topics never compete, and a topic the question is not about takes no part.
3. **Inside a group.** Two documents that make the same claim agree, and neither drops the other. Between two that disagree: inside one version chain and owner scope, the newer `effective_from` wins, or the one that `supersedes` the other. Across different kinds of document, the higher authority wins whatever the dates. The order is wording, endorsement, rule, guide, then brochure and FAQ.
4. **Anything else is a conflict.** Two different claims that none of these separate set a conflict flag. So does a document that covers only some customers, such as an endorsement that only the policies carrying it receive, against one that covers everyone: who is asking decides, and the agent cannot see that. The core turns the flag into a handoff with the reason "documents disagree", because a person should decide, not a guess.

The newest document is not always the one to trust: a new brochure does not change what the policy wording says. Where one document wins, the winner is delivered and the loser is dropped before the model reads anything. A document that loses on one topic but wins, or agrees with another document, on another topic in the same question stays. Only a topic with at least two applicable documents counts as a win or an agreement; a topic with one document is no group at all.

Each document carries these front matter fields: `topics`, `applies_to` (product, customer group and dates), `effective_from`, `effective_to`, `authority`, `version_chain`, `owner_scope` and `supersedes`. `topics` names each rule the document states, with what the rule is about and the claim the document makes on it:

```yaml
topics:
  cg-flood-home-essentials:
    about: Flood on Home Essentials
    claim: f-flood-he
```

A document with a single plain `topic: <name>` and no claim is read as one topic whose claim is the document itself.

## Step 1: read the conflict questions and predict (5 minutes)

Filter the `conflict` slice in `packs/<your-pack>/eval/questions.md`. Find the pairs where the newer document has lower authority, or a different scope. Then write `predictions/lab4-authority.md`: how many of those questions you think the agent answers wrongly now. Commit and push it. Step 5 needs it pushed first.

## Step 2: write the authority rule (15 minutes)

File: [app/context.py](../../../app/context.py#L137-L138), `apply_authority(index, doc_ids, query)`, between `# YOUR TURN start` and `# YOUR TURN end`. It returns two things: the set of documents to drop, and a conflict (or `None`).

These helpers sit just above it and are part of what you read and complete:

- [`_applicable(meta, query, group_products)`](../../../app/context.py#L93-L110): false when the document starts after the evaluation date, ended before it, or is for a product other than the one the question names while a sibling is for the product it names.
- [`_beats(a, b)`](../../../app/context.py#L118-L134): true when `a` wins, false when `b` wins, `None` when no rule picks a winner. Different customer groups in `applies_to`: `None`. Same chain and scope: `supersedes` first, then the newer `effective_from`. Different chain or scope: the better `AUTHORITY_RANK` ([L20](../../../app/context.py#L20): wording 0, endorsement 1, rule 2, guide 3, brochure and FAQ 4).
- `_topics(meta)` and `_claim(meta, topic, doc_id)`: the topics a document states, and its claim on one of them.
- `_in_question(index, members, topic, query)`: true when the question is about the topic. Every word of the topic's `about` but one must appear in the question (every word when it has two or fewer).

In `apply_authority`: group the delivered documents by topic; skip a group of one and a topic the question is not about; keep only the applicable members; inside a group, a member beaten by a member with a different claim loses there; drop a document that loses in every group it sits in; if more than one member of a group survives and two different claims have no winner, return a conflict `{"reason": "documents disagree", "topic": ..., "docs": [...]}`.

Where it runs: [the assembly step](../../../app/context.py#L138) calls it when `authority_rule` is `on`, drops the losers from the candidates, and records them as `dropped_docs`. [The core](../../../app/core.py#L248) turns a conflict into a handoff whose reason is "documents disagree", and whose note names the documents. The assembly you wrote in part 1 makes that call, and the core part is shipped. Lab 5 adds a fuller note, and Saltmarsh's pack keeps this rule in lab 5's required rules whatever you decide here.

## Step 3: run the tests and fix (4 minutes)

```bash
python -m pytest challenges/challenge-4-related-docs/part-2-when-documents-disagree -q
```

[test_authority.py](test_authority.py) writes a twenty-one-document pack into a temporary folder and checks, with the stub model: a document for another product or not in force on 2026-11-01 is not part of a conflict; a newer document wins inside one version chain and one that supersedes beats the date; a higher authority wins across kinds even when the other document is newer; any other pair of different claims is a conflict; two documents with the same claim agree and are both kept; a topic the question is not about takes no part; a document for some customers against one for everyone is a conflict; documents of different topics are never dropped for each other; the winner is delivered and the loser is not; and a conflict leaves a handoff with the reason "documents disagree". On the starter every test fails with `NotImplementedError` except `test_the_evaluation_date_is_fixed`, which already passes.

## Step 4: read the verdict of the context run, decide, keep or revert (8 minutes)

```bash
python -m harness diff <context-run> <last-kept-run>
```

It regrades both runs, then prints fixed, broken, the sign-test p and the verdict. Reference numbers for Saltmarsh: 6 fixed and 2 broken, verdict "inconclusive", and context tokens up 53 percent against a budget of 50 (within budget: no).

The rule: keep if the verdict is "evidence of improvement on this set" and the tokens are within the 50 percent budget. With no evidence either way, keep only if the run is cheaper or simpler than its parent. Otherwise revert. Run `python -m harness keep <context-run>` or `python -m harness revert <context-run>`, then add one entry to `LAB-LOG.md`. The run in `runs/kept.json` is the parent of the next run.

## Step 5: screen the rule (5 minutes)

Push the prediction from step 1 first. Then screen with the rule off and on:

```bash
python -m harness screen --pack <your-pack> --set authority_rule=off
python -m harness screen --pack <your-pack> --set authority_rule=on
```

Read the `conflict` slice of each, and for each conflict pair which document is delivered ([the screen code](../../../harness/screening.py#L94-L123) records the delivered chunks in `cases.jsonl`). Reference numbers for Saltmarsh: 10 conflict questions, the right document delivered in 0 before the rule and 3 after it. A screen is exact and has no verdict.

## Step 6: commit and start the second full run (3 minutes)

```bash
git add -A
git commit -m "Lab 4 part 2: the authority rule"
python -m harness run --pack <your-pack> --set authority_rule=on --parent <last-kept-run>
```

The parent's settings load, so the context setting you kept in step 4 stays.

## Step 7: while it runs

Read two conflict questions that the screen moved, and draft your explanation. No minutes are added here.

## Step 8: read the diff, decide, explain (8 minutes)

```bash
python -m harness diff <authority-run> <last-kept-run>
```

Reference numbers for Saltmarsh: 0 fixed, 0 broken, verdict "inconclusive". Apply the same rule as in step 4. Keep or revert with the same commands (`python -m harness revert <authority-run>` for a revert), and log it. Plain `python -m harness revert` with no run id undoes the last kept run, which is not what you want for a candidate you never kept.

Explain the run in the lab log, as claim, evidence, cost and next. The shape:

> Kept (or reverted). Context fact recall moved `<points>` points; answer success verdict `<verdict>` on `<n>` questions. Context tokens rose `<percent>` percent against a budget of 50. Authority rule kept (or reverted): the right document was delivered in `<x>` of `<y>` conflict cases, verdict `<verdict>`. Next: lab 5 adds tools and the rules that decide when the agent must not act.

For Saltmarsh the reference values are: context fact recall moved 2 points on 60 eligible questions; answer success was 32% at the start of lab 4, 38% with context and 32% with the authority rule on top; 32% for the run kept at the end of lab 4.

## Step 9: commit (2 minutes)

The repository works and the log is up to date. Check the lab with `python -m harness gate 4`. It reads your own records only: that your prediction was committed before your first record, that the screens and runs share every setting but the lab's own, that each run is comparable with its parent, that each run has a keep or revert decision, and that `results.md` cites only your own runs.

## Other companies

| Company | Old document | Current document |
|---|---|---|
| Quillon | an old price list | the current quote rules |
| Juniper Lane Clinic | an old preparation leaflet | the current preparation rule |

These are measured on the synthetic packs and are a prediction to test on your own pack, not a rule.
