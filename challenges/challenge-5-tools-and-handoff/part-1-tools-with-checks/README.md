# Challenge 5, part 1: tools with checks

The model may ask for a tool. It is only a request. The core decides whether the request is valid, whether it belongs to the person asking, and whether it has been made before. You write those checks, a safe-repeat store, and the grader that reads the mock company system to see what really happened. Then you run the smoke set and start the first full run with tools on. The worked company is Juniper Lane Clinic. The packs are synthetic, and a real clinic needs clinical and legal review that this course does not give. Run every command from the repository root.

80 work minutes plus waiting on the reference laptop. Step 2 runs the tool slice (a few minutes). Step 8 runs the smoke set (4 minutes with a GPU, about 11 minutes (estimated) CPU only for Juniper Lane) and then starts the first full run. A full run takes 13 minutes with a GPU and 29 minutes CPU only on the reference laptop. Part 2 reads it after its first steps, so this part adds only the smoke wait.

## The idea, from zero

A tool is a function the agent can ask the system to run: look up an account, book a slot, hand over to staff. The model writes the request as text: a tool name and arguments. Nothing in that text is trustworthy. The model may invent a tool, leave out a field, give a number as a word, or copy an account number from the conversation that is not the asking person's own. So the core, not the model, does four things:

1. **Validate the arguments.** Unknown tool name, missing field, extra field, wrong type, a value outside the allowed list: refuse it, and tell the model why as a tool message so it can try once more.
2. **Bind the principal.** The principal is the person the adapter proved is speaking. The core fills the account from it. An argument that names another account is refused and logged. An unverified principal is refused for account tools.
3. **Make a repeat safe.** Networks fail, and a client that does not get a reply asks again. Mail servers and web clients retry after a timeout, so a repeat is normal. The same request id must never book twice.
4. **Check the final state.** A reply can say "booked" while nothing is booked. The grader reads the mock system's state after each case, and compares it with the state the question expects.

The tools, per company. Every tool takes the principal from the core.

| Company | Tools |
|---|---|
| Quillon | `lookup_account`, `create_quote`, `book_demo` |
| Juniper Lane Clinic | `check_slots`, `book_appointment`, `hand_off` |
| Saltmarsh Mutual | `lookup_policy`, `check_claim`, `open_claim` |

Handoff is an output of the core for all three companies. At the clinic the core carries an urgent handoff out through the `hand_off` tool, so it leaves a final state the harness can check: a staff task with its urgency.

## Step 1: write and push your prediction (5 minutes)

In `predictions/lab5-tools.md` write how many of the planted tool questions pass now, and the kind of failure you expect most. Commit and push it.

## Step 2: run the tool questions and read the failures (8 minutes)

```bash
python -m harness run --pack <your-pack> --slice tool --set tools=on --parent <last-kept-run>
```

The `tool` slice is the tool questions only. On the starter the tools are unchecked. Read each failure and put it into one of four kinds: bad arguments, wrong account, repeated action, wrong state. For Juniper Lane the reference run had 16 tool questions and 0 passed before the checks.

## Step 3: validate arguments (10 minutes)

File: [app/tools/__init__.py](../../../app/tools/__init__.py#L75-L117), `validate(pack, name, args)`. The allowed tools and their fields are in the table [`SPECS`](../../../app/tools/__init__.py#L24-L56). Return the cleaned arguments, or a reason: unknown tool; arguments that are not valid JSON; a field the tool does not have (the reason says who is calling comes from the system); the wrong type; a value outside an `enum`; a required field that is missing. When the call is refused, [`result_for_model`](../../../app/tools/__init__.py#L190-L197) gives the model the reason as a tool message.

## Step 4: bind the principal (12 minutes)

File: [app/tools/__init__.py](../../../app/tools/__init__.py#L156-L158), `ToolBox.bind(name, args, principal, state)`.

- A verified principal has an `account_id`. An unverified principal has none for tool purposes.
- Quillon: `lookup_account` and `create_quote` need a verified principal; an `account_id` or email that is not the principal's own is refused; the account is filled in from the principal.
- Juniper Lane: `book_appointment` needs a verified principal; a `patient_id` must be one of the patients the principal's account owns (the fixture lists them); with exactly one patient it is filled in; with several the call is refused and the reason says the patient is missing.
- Saltmarsh: `check_claim` and `open_claim` need identity first (the person proved a policy number and date of birth with `lookup_policy`); a policy or claim of another account is refused.
- A refused call is still recorded, with its reason. [`ToolBox.run`](../../../app/tools/__init__.py#L167-L187) never lets a refused call reach the mock.

## Step 5: idempotent requests (18 minutes)

An **idempotent** action is one that has the same effect whether you do it once or ten times. Two files:

- [app/idempotency.py](../../../app/idempotency.py#L18-L39), `IdempotencyStore`. `reserve(key, request_hash)` returns `"new"` the first time, `"in_progress"` if the same key is still being worked on, `"done"` with the stored reply once finished, and `"conflict"` when the same key came with different text. It must be atomic: of two callers at the same moment exactly one gets `"new"`. Use a lock around the check and the write. `complete` stores the reply. `release` frees a key whose request failed, so a retry can run.
- [app/core.py](../../../app/core.py#L241-L243), `handle`: the key is (principal id, conversation id, request id) plus a hash of the request, so nobody can read another principal's reply by guessing an id. Reserve before acting; answer a concurrent duplicate with "in progress"; store the reply when the action is done. [`idem_key`](../../../app/tools/__init__.py#L71-L72) builds the key passed to every mock call, so a retry that does reach the mock still never repeats the action; the mock stores each key's receipt and replays it.

Write down the three cases the tests check: a request id sent by another principal, two concurrent duplicates, and a lost response that is retried.

## Step 6: the final-state grader (15 minutes)

File: [harness/graders/tool.py](../../../harness/graders/tool.py#L11-L24). Assistant-written code is allowed here. Read it carefully, with its trap tests. The grader reads each case's `eval` block (the attempted calls, with the refused ones and their reasons, and the receipts) and the mock's state after the case, and scores four things: the right tool, valid arguments, no forbidden attempted call, and the right final state. A refused forbidden call still fails the case: an attempt is an attempt. A reply that says "booked" while the mock holds nothing must fail.

Where the mock's state comes from: `MockClient.state()` in-process, or the endpoint `GET /mock-state` of the running app, or `GET /ns/<namespace>/state` of the mock server (`mock_api/server.py`) when `MOCK_API_URL` is set. The harness sets the principal for each case with the test header `X-Test-Principal`, which the server accepts only in test mode with the exam token. The comparison itself is in [harness/graders/state.py](../../../harness/graders/state.py#L135-L146).

## Step 7: run the tests (4 minutes)

```bash
python -m pytest challenges/challenge-5-tools-and-handoff/part-1-tools-with-checks -q
```

[test_tools.py](test_tools.py) uses a scripted model and the packs' own fixtures. It checks that a call naming another account or patient is refused and never reaches the mock; that the principal is never taken from arguments; that an unknown tool, a missing field, a wrong type and a value outside the list are refused; that an unverified principal is refused for account tools; that a repeated request leaves one booking; that a request id sent by another principal is not answered from the first principal's reply; that two concurrent duplicates run one action and the second gets "in progress"; that a lost response retried with the same request id returns the stored reply; and that the grader fails a reply that says "booked" while the mock holds nothing. On the starter all twelve fail: the grader test with `NotImplementedError`, the rest with a `ValueError` or `IndexError` (no tool call was recorded) or an `AssertionError`, because binding is not written yet.

## Step 8: smoke test, commit, start the first full run (8 minutes)

```bash
python -m harness run --pack <your-pack> --smoke --set tools=on --parent <last-kept-run>
```

The smoke set is 40 cases (30 questions and 10 attacks). It is a first look, not a verdict. Read the tool verdicts case by case in the dashboard, and write a smoke table (case, verdict, reason) in `results.md`. Then commit (a run stops on uncommitted changes) and start the full run:

```bash
git commit -am "Lab 5 part 1: tools with checks"
python -m harness run --pack <your-pack> --set tools=on --parent <last-kept-run>
```

It is the first of lab 5's two full runs. While it runs, read the fixture in `packs/<your-pack>/tools/fixture.json` and write by hand the final state of two cases. Write the `tools` run id in `LAB-LOG.md`. Do not run the gate yet: it needs a complete run, so run it at the start of part 2.

## Reference numbers (Juniper Lane Clinic)

| Measure | Value |
|---|---|
| Tool questions | 16 |
| Pass before the checks | 0 |
| Pass after the checks | 2 |
| Bookings from the planted repeat, before | 0 |
| Bookings from the planted repeat, after | 1 |

For the other two companies, tool questions 16 (Quillon) and 15 (Saltmarsh), pass after 7 and 1. These are measured on the synthetic packs and predict, not prove, what your pack does.
