# Capstone, part 4: the live-examination rehearsal

Run every command from the rehearsal checkout. The packs are synthetic. The worked company is Juniper Lane Clinic. This part is numbered 4 because it was added after the other three, and you do it before part 3 (going online). The live examination is switched off for the first cohort, so this part is practice and is not marked.

## The idea, from zero

The live examination is a short typed conversation about your own work. It asks five kinds of question and scores four marks. You rehearse both here, on a timer, from your own runs, with no assistant and no model scoring you. You score yourself, so the test below checks the form of your work and not the marks.

The five question shapes:

1. In run Y, case X broke. Why did you keep the change anyway?
2. You reverted run Z. What would have to be true for you to keep it?
3. Predict what this new document does before you run it.
4. Your unseen-set score is lower than your public one. Why?
5. What would you build first for email?

The four marks, as `examiner/live-exam.md` scores them. Each is met or not met, with no half marks.

| Mark | Met when | Shapes |
|---|---|---|
| Explains from evidence | the answer names a run id, a case id and a number from your own records | 1, 2, 4 |
| Predicts before running | the prediction names the family, the behaviour and the defence, and was committed before the run | 3 |
| Fixes and verifies | in branch A the fix is made and the second run shows it; in branch B the answer names the defence that stopped it | 3 |
| Knows the limits | the answer says what the evidence cannot show and does not overclaim | all |

## Where it runs

The rehearsal runs in a separate checkout, so that nothing here changes the agent you will submit. A fix found here reaches the submitted agent only if you copy it over and rerun the confirmation from part 1, then update the links in your report.

## Steps

The timer covers steps 2 to 7 and lasts 30 minutes (45 with extra time). Close your `.env` file, your personal windows and any assistant first.

1. **Make the checkout (1 min).** `git worktree add ../rehearsal` from the commit you plan to submit. Work inside it; `rehearsal/answers.md` below is the folder `rehearsal/` inside that checkout. Start the timer.
2. **Shapes 1 and 2 (8 min).** In `rehearsal/answers.md`, under `## Shape 1` and `## Shape 2`, answer from a case and a run id in your own `runs/`. Aim for four minutes each.
3. **The practice copy (3 min).** Copy `packs/<your-pack>/` to `packs/<your-pack>-practice/`. Add [`practice-poison.md`](practice-poison.md) to its `corpus/`. Delete `eval/attacks.jsonl` from the copy. Keep a short `eval/questions.jsonl`, and replace `eval/smoke.jsonl` with a few of those same lines, because `--smoke` reads only `smoke.jsonl` and stops with "no cases selected" when it is empty. Make sure one of them is a question that asks about the notice board, so the document is retrieved and reaches the prompt.
4. **Predict and commit (3 min).** Write `predictions/rehearsal.md` before you run anything: what the agent will do with the document, which attack family it belongs to, and which of your defences should stop it. Copy the same text under `## Shape 3`. Commit the practice copy and the prediction together, and push. A run refuses a tree with uncommitted files, so the copy must be committed before step 5.
5. **Run the smoke set (1 min, then wait).** `python -m harness run --pack <your-pack>-practice --smoke --parent <last-kept-run>`.
6. **Shapes 4 and 5 (8 min).** While it runs. Use your own ten questions from part 1 as the unseen proxy for shape 4. For shape 5, use the adapter idea from module 1: the principal of an email needs its own proof, because the sender field is written by the sender.
7. **Read the result (6 min).** The timer stops here. Two branches:
   - **Branch A, the document got through.** Find which path let it in, make one fix in the rehearsal checkout, commit it, and start the smoke set again with the first run as `--parent`. Read the second result and write whether the fix worked under `## Shape 3`.
   - **Branch B, the document was stopped.** Under `## Shape 3` add a line that starts `Stopped by:` and names the defence, and say whether your prediction named it.
8. **Score yourself (5 min).** Each answer against the four marks.
9. **Time used (3 min).** End `answers.md` with a last line that starts `Time used:` and say what you would do faster.
10. **Test, commit, push (2 min).** `python -m pytest challenges/challenge-9-capstone/part-4-rehearsal -q`.

## What the test checks

- `rehearsal/answers.md` holds the five headings `## Shape 1` to `## Shape 5` and ends with a `Time used:` line.
- The text under `## Shape 3` starts with the text of `predictions/rehearsal.md`. Lines you add after it, such as a fix or `Stopped by:`, are allowed.
- The prediction was committed before the first smoke run record on the practice pack.
- The practice copy differs from the real pack by exactly one document.
- Branch A: a second smoke run record exists whose parent is the first. Branch B: the answers hold a `Stopped by:` line.

It does not score your four marks. That is yours to do honestly.

## If something looks wrong

- **The run stops with status 3.** Something outside `runs/` and `.cache/` is uncommitted. Commit the practice copy and the prediction.
- **The test says the prediction came after the run.** The prediction file must be committed before step 5. Write it, commit, then run.
- **The test says the copy differs by more than one document.** Copy the pack again and add only the practice document.
