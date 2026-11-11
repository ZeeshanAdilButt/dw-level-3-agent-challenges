# Capstone, part 2: the one-page report

Run every command from the repository root. The packs are synthetic. The worked company is Quillon. The numbers below were measured on the synthetic pack with the reference build. No run starts in this part.

## The idea, from zero

A reader of your report will ask one question about every number: where did it come from? If the answer is "I remember it", the number is worth little. So in this report every number a run produced is a **link** to the file the harness wrote. The text of the link holds the number and the metric. The target holds the file and the name of the metric inside it. A command, `report-check`, opens each file, finds the metric, and compares the number you wrote with the number stored.

Numbers that are not measurements are plain text and are not checked: settings (`temperature 0.2`), design counts (`8 attacks per family`) and dates.

The report is also honest about what it cannot show. The confirmation used the public questions your choices were made on. The report says so in its limits, and it says the baseline was rerun on today's code.

## What the starter gives you

| What | Where | Lines |
|---|---|---|
| The template, with the eight sections in order | [challenges/challenge-9-capstone/REPORT.template.md](../REPORT.template.md) | all |
| How a link is read and its number compared | [harness/report_check.py](../../../harness/report_check.py#L41-L52) | 41 to 52 |
| Link finding, file reading and the 600-word limit | [harness/report_check.py](../../../harness/report_check.py#L63-L86) | 63 to 86 |
| How words are counted (comments and link targets do not count) | [harness/report_check.py](../../../harness/report_check.py#L55-L60) | 55 to 60 |

You write no Python here. You write `REPORT.md` and `LAB-LOG.md`. Start `REPORT.md` as a copy of the template.

## What a link can point to

| File | Holds | Example target |
|---|---|---|
| The confirmation, written by `harness confirm` | the best side and the baseline side, by majority | `runs/confirm-r031.json#best.answer_success` |
| A run record | totals and metrics of one run | `runs/r012/run.json#totals.latency_p95_ms` |
| A run record, by family | attacks passed in each of the six families | `runs/r012/run.json#metrics.security_by_family.doc-injection` |

Three rules make the check pass:

1. The **first number** in the link text is the one that is checked. Write the number first: `[9000 ms p95 latency](...)`, not `[p95 9000 ms](...)`, because the check would read the 95 of `p95`.
2. A fraction is written as a percentage to the rounding you show (`0.64` is `64%`), a count exactly, a time in milliseconds as stored, and a cost in dollars as stored.
3. A number you computed yourself, such as a gain or a price you worked out from tokens, is stored in no file, so it cannot be linked. Put it in `LAB-LOG.md`, and in the report link the numbers it was computed from. The one exception is the hosted-equivalent median cost per answer: the run record stores it as `totals.hosted_equivalent_cost_p50`, so link that.

`harness diff` prints a comparison but does not write a file in this build. Name the cases that broke in plain text (case ids are not numbers), and link the answer success of the run that did not help.

## Steps

1. **Check the inputs.** The six confirmation runs from 9.2 have ended, `runs/confirm-<id>.json` exists, and `python -m harness validate` is clean.
2. **Read a weak and a strong report** on the same runs. List what the strong one does: every measured number points to a file, a failure is named, a limit is stated.
3. **Sections 1 and 2.** The settings are plain text, one line each. Each kept change gets its gain and its cost. Link the two run values the gain comes from and the cost; write the gain itself in plain text as points, such as 12 points (a percent sign on an unlinked number fails the test).
4. **Section 3.** At least one change that did not help, the case ids that broke, and your best guess why.
5. **Section 4.** The stacked table of lab 7: for each family, the pass rate as a link to `metrics.security_by_family.<family>`, written as a percentage (6 of 8 is 75%), because the stored value is a fraction and a link text of just `6` fails. The `8` is plain text.
6. **Section 5.** The two-path table of lab 8. Say which path the best setup ran on, and that the other path's numbers come from the 40-case smoke runs. Each cost and p95 is a link to its run record.
7. **Section 6.** The best setup's confirmed public score, its own-ten score and the gap, with links to the confirmation file and the own-ten run record, the ids of the own-ten cases that failed, and one reason. The examiner's unseen set is not known yet, so do not explain it. Say the gap is a guess from ten questions.
8. **Section 7.** Limits: the packs are synthetic and one company; code checks are proxies; 48 attacks cannot show safety; the public set is a sample and the choices were made on it; the baseline was rerun on today's code; the model can answer differently on another day.
9. **Section 8.** Five sentences. Email arrives as a message posted to your server, with a message id and an `In-Reply-To` and `References` chain that tells you which conversation it belongs to. A phone call becomes text through a speech service, and your core answers the text. Neither is built. Say what the principal would be on each channel and who proves it. Use the adapter idea from 1.2 and 5.4: the core never reads who is speaking from the message text.
10. **Check.** `python -m harness report-check` (every linked number matches its file, at most 600 words), then `python -m pytest challenges/challenge-9-capstone/part-2-the-one-page-report -q`. Delete the comment at the top of the template first: the check skips comments, but the report should not carry it. Fix every finding.
11. **Explain the run** in `LAB-LOG.md` as claim, evidence, cost, next.
12. **Commit and push.**

## Where each number comes from

| In the report | Source |
|---|---|
| Best and baseline answer success | `best.answer_success`, `baseline.answer_success` in the confirmation |
| Cost per answer | `totals.cost_p50` in the run record of the path (a local run pays 0); for a local run link `totals.hosted_equivalent_cost_p50` and label it hosted-equivalent |
| p95 | `totals.latency_p95_ms` in the same record, in milliseconds |
| Attacks passed by family | `metrics.security_by_family.<family>` in a run record |
| Own-ten score | `totals.answer_success` in the own-ten run record |

## Reference results (Quillon)

Best setup 42% against baseline 37% by majority of three runs per side. Cost per answer 0.0000 dollars and p95 8717 ms. The reference build has no own ten, so there is no reference gap. Attacks passed after the last defence, of 8 per family:

| Family | Quillon |
|---|---|
| doc-injection | 8 of 8 |
| message-injection | 6 of 8 |
| other-person | 8 of 8 |
| internal-content | 8 of 8 |
| system-prompt | 8 of 8 |
| domain-harm | 6 of 8 |

| Company | Best | Baseline | p95 (ms) |
|---|---|---|---|
| Juniper Lane Clinic | 35% | 33% | 15578 |
| Saltmarsh Mutual | 39% | 33% | 13386 |

These are measured on the synthetic packs.

## If something looks wrong

- **`report-check` says a number does not match.** Open the file and the metric it names, and copy the stored value, rounded the way you show it.
- **It says the file has no metric.** Walk the path by hand with the keys separated by dots, from the top of the JSON file.
- **The test says `AssertionError: report has no linked numbers`.** The report is still the template, or its numbers are plain text.
- **It says a number is plain text.** A percentage, a dollar amount or a time that is not a link. Link it, or remove it if no run produced it.
- **More than 600 words.** Cut sentences, not links. Table cells count, link targets do not.
