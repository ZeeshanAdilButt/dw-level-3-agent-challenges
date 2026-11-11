# Challenge 1, part 3: graders, records, three runs

You write three graders, learn to read a run record, write your first prediction, and start three identical full runs with one command. The runs are read in part 4. Run every command from the repository root. The data is synthetic.

## The idea, from zero

A **grader** is a small function that reads one stored reply and says pass or fail, with a reason. It never calls the agent. That rule matters: the harness stores every reply, and `python -m harness diff` can later grade the stored replies of two runs with the same grader. If a grader called the live agent, an old run could not be graded again.

Each question in `packs/<your-pack>/eval/questions.jsonl` lists **key facts**: the things a correct answer must say. A key fact is a small record ([the docstring](../../../harness/graders/fact.py#L1-L9)):

- `entity`: what the fact is about, for example `Pro plan`.
- `forms`: the accepted ways to write the value, for example `$38`, `38 dollars`.
- `qualifiers`: words that must sit in the same sentence, for example `per month`, `monthly`. They stop `$38 per year` from passing for a monthly price.
- `rival_forms`: the accepted forms of other values for the same attribute and entity, for example `$45`. They catch a reply that states the wrong price.

## Step 1: the three graders (35 min)

Run the tests first and read the three failures (5 min). Each ends in `NotImplementedError: YOUR TURN: ...`.

```bash
python -m pytest challenges/challenge-1-baseline/part-3-graders-and-runs -q
```

**`harness/graders/fact.py` (12 min).** [`check_fact`](../../../harness/graders/fact.py#L12-L13) returns `{"ok", "reason", "sentence"}`. The text helpers are shipped in [`text.py`](../../../harness/graders/text.py): [`sentences`](../../../harness/graders/text.py#L23-L24), [`has_form`](../../../harness/graders/text.py#L44-L49) (an accepted form that does not sit inside a longer word or number, so `$38` is not found in `$380`), [`has_entity`](../../../harness/graders/text.py#L71-L77) and [`is_negated`](../../../harness/graders/text.py#L80-L82) (a cue such as "not" or "never" that is not part of the value itself). A reply states the fact when one sentence holds a form of the value, names the entity, holds at least one qualifier (if the fact has any) and is not negated. Then a second pass: a different value for the same attribute and entity fails the reply, unless that same sentence also states the right value (a comparison). The reasons are `ok`, `missing`, `entity`, `qualifier`, `negated` and `rival`.

The traps the test pins, one each: a number tied to the wrong entity ("The Team plan costs $38"), a negated fact ("does not cost $38"), the value and the entity in different sentences, a missing qualifier ("$38 per year"), a different value for the same attribute and entity, and a number inside a longer number.

**`harness/graders/citation.py` (8 min).** [`grade_citations`](../../../harness/graders/citation.py#L14-L15) takes the cited ids, the documents the model was given (`delivered`) and the gold sources. A citation is valid when its document was delivered. The answer is cited correctly when at least one gold source is cited and no cited id is invalid. Precision is the cited ids that are gold, divided by the cited ids. Trap: a cited id that was never delivered. It returns a dict with the keys `cited` (the ids, each once, in order), `valid` and `invalid` (lists), `gold_cited` (true or false), `cited_correctly` (true or false), and `precision_num` and `precision_den` (whole numbers, not a ratio).

**`harness/graders/recall.py` (10 min).** [`recall_at`](../../../harness/graders/recall.py#L8-L9) counts the gold documents found in the first `k` ranked chunks, divided by the gold documents. Several chunks of one document count once. Trap: two chunks of one document. Nothing to find gives 0, not 1. Rerun the tests until the traps pass.

## Step 2: records and the prediction (15 min)

**Read a record (7 min).** The folder [`sample-record/runs/r000/`](sample-record/runs/r000) holds a small shipped record. `run.json` says exactly what ran. Its `manifest` holds the code commit and tree, the prompts, the corpus hash, the index settings, the model, the tool fixtures, the grader version and the question-set version, and the `fingerprint` is the hash of that manifest ([`build_manifest`](../../../harness/fingerprint.py#L77-L95)). Two runs are **comparable** when their pack, question-set version and model match and at most one setting differs. The three noise runs differ in no setting. `cases.jsonl` has one line per case: the spec, the stored steps with each reply and its `eval` block, and the grader's verdict. Open the first line and say what each field is. `run.json` also carries a digest of itself and of `cases.jsonl`, so an edit made after the run is caught: `validate`, `regrade` and `keep` refuse the record, and `/health` shows its fingerprint as `edited`.

**Write the prediction (4 min).** In `predictions/lab1-noise.md` write how many of the 148 cases (100 questions and 48 attacks) you think will change between run 1 and run 2, whether you expect more fixed or more broken cases, and one sentence of reasoning. Commit and push it before the first run. Each run record stores the last commit that touched `predictions/` ([`prediction_commit`](../../../harness/fingerprint.py#L67-L74)); the examiner reads the push time from GitHub.

**Validate (4 min).**

```bash
python -m harness validate
```

It checks the schema of every record under `runs/` ([`validate_run_dir`](../../../harness/schema.py#L75-L97)). With none yet it says `nothing to validate`.

## Step 3: commit, start three runs, write while they go (25 min)

A run copies the committed tree to `.cache/snapshots/<run_id>/` and executes from there ([`make_snapshot`](../../../harness/run.py#L105-L116)), so editing while it goes changes nothing. An uncommitted change stops the run before it starts ([`dirty_paths`](../../../harness/run.py#L88-L102)). Commit your graders and the prediction (5 min), then:

```bash
python -m harness run --pack <your-pack> --repeat 3
```

(4 min). It prints the resolved settings first, then runs the same settings three times from one snapshot. `--repeat` turns the cache off, so no reply is reused: three runs that share a cache would only copy the first ([`main`](../../../harness/run.py#L225-L269)).

Reference timing, per run: 13 minutes with the GPU and about 29 minutes (estimated) on the CPU only for Quillon (Juniper Lane 13 and 29, Saltmarsh 13 and 29). Three runs take three times that. Start them at the end of a session.

While they run, write the first lines of `LAB-LOG.md`: the question, your prediction and the settings (9 min). Then read two cases of the sample record and say why each passed or failed (7 min). Do not commit `runs/` yet; part 4 does that once the runs have finished.

| Company | A key fact a grader must catch (the trap) |
|---|---|
| Quillon | question q-001: Pro plan = $38, with the qualifier "monthly billing"; the number alone must not pass |
| Juniper Lane | question q-001: Fasting blood test = EUR 48, with the qualifier "self-pay"; the number alone must not pass |
| Saltmarsh | question q-008: Home emergency rider = £4.90, with the qualifier "per month"; the number alone must not pass |

## The tests

- Acceptance, failing on the starter with `NotImplementedError: YOUR TURN: ...`: `test_fact_grader`, `test_citation_grader`, `test_recall_grader`, each over fixed fixture replies with 8 trap cases between them. Acceptance `test_prediction_first` fails with `AssertionError: no prediction commit before the first run record` until a prediction commit exists and comes before the first run record in your own `runs/`.
- Invariant, passing on the starter: `test_validate_sample` (the shipped validator accepts the sample record) and `test_the_prediction_checker_on_fixed_records`.

## If something looks wrong

- **The fact grader passes `$380` for `$38`.** Match whole numbers only: a form that ends in a digit must not be followed by another digit.
- **A comparison fails as a rival.** Check that you let a sentence pass when it also holds the right value.
- **The run stops with `uncommitted changes`.** Commit, then run again. `runs/` and `.cache/` are ignored by this check.
