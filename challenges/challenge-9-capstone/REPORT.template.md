# Report: <your company> agent, Dev Weekends Level 3

<!--
How to fill this page. Delete every comment before you submit.
- One page: at most 600 words. `python -m harness report-check` counts them.
- Every number a run produced is a link: the number and the metric in the text (write the number first), the file and the metric name in the target.
  Example: [64% answer success](runs/confirm-r031.json#best.answer_success)
  A percentage is written as shown on the run record (64% for 0.64). A count is written exactly. A time is written in ms and a cost in dollars, as stored.
- Settings, design counts and dates are plain text. Do not link them.
- Say what happened, not what you hoped. A change that did not help belongs in section 3.
-->

## 1. The best setup

One line for each setting that differs from the starter, with the run that kept it.

- Retriever: ...
- Chunking: ...
- (continue)

Model path used for the best setup: ...

## 2. Each kept change, with its gain and its cost

| Change | Gain (two linked run values, then the gain in points) | Cost (linked) |
|---|---|---|
| ... | ... | ... |

Confirmation: the best setup against the baseline, by majority of three runs each, the baseline rerun on today's code.

## 3. What did not work

At least one change that did not help, the cases that broke (ids), and your best guess why.

## 4. Security pass rate by family

| Family | Pass rate (linked, as a percentage) | Attacks |
|---|---|---|
| doc-injection | ... | 8 |
| message-injection | ... | 8 |
| other-person | ... | 8 |
| internal-content | ... | 8 |
| system-prompt | ... | 8 |
| domain-harm | ... | 8 |

## 5. Cost per answer and p95, on both model paths

State which path the best setup ran on. State that the other path comes from the 40-case smoke runs.

| Path | Cost per answer | p95 |
|---|---|---|
| local | ... | ... |
| hosted | ... | ... |

## 6. Public score against my own ten questions

The best setup's confirmed public score, its own-ten score, the gap, the ids of the own-ten cases that failed, and one reason. Say the gap is a guess from ten questions.

## 7. Limits of this evaluation

- ...

## 8. How email and phone would plug in

For each channel: how the message arrives, what the principal would be, and who proves it. Say neither is built.
