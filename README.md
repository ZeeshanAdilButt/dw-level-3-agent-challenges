# Support and Knowledge Agent: course template

This is the starter for **Dev Weekends Level 3: Build a Support and Knowledge Agent, and Prove It Works**, a course by Zeeshan Adil. Create your own repository from this template. The course chapters walk you through every part.

You pick one company, build a cited support or knowledge agent on its documents and three mock tools, and then run one measured experiment per lab. Each time you keep or revert the change based on a per-case diff.

## What is here

| Folder | What it holds |
|---|---|
| `app/` | The agent: one channel-free core, the chat adapter, retrieval, tools, rules and security |
| `harness/` | Runs the questions, grades every reply, records each run, and compares runs |
| `dashboard/` | The impact dashboard, served by the app at `/dashboard` |
| `packs/` | The three companies: documents (`corpus/`), questions and attacks (`eval/`), tool fixtures (`tools/`) |
| `mock_api/` | The three mock tools and their rules |
| `challenges/` | One folder per lab, one part per folder, each with a README, a `results.md` and tests |
| `config/` | `settings.toml` (your settings, one section per lab), prices, ids |
| `reference-runs/` | Summaries of the reference runs, so you can compare your numbers with ours |
| `runs/`, `predictions/` | Empty. Your run records and predictions go here |
| `LAB-LOG.md`, `REPORT.md` | Your decision log and your one-page capstone report |

The parts marked `YOUR TURN` are yours to build. Until you build them they raise `NotImplementedError`, or the dashboard shows "Panel not built yet".

## Setup

1. Install Python 3.11 or newer, Git and [Ollama](https://ollama.com).
2. Make a virtual environment and install the requirements:

   ```bash
   python -m venv .venv
   ```

   Activate it, then run:

   ```bash
   pip install -r requirements.txt
   ```

3. Make sure `.gitignore` has a `.env` line before your first commit. If you use the hosted model path, your key lives in `.env` and must never be committed.
4. Pull the two local models:

   ```bash
   ollama pull qwen3:4b-instruct
   ```

   ```bash
   ollama pull nomic-embed-text
   ```

5. Run the doctor. It checks your machine and picks the local or the hosted model path:

   ```bash
   python tools/doctor.py
   ```

6. Pick your company in `config/settings.toml`: `pack = "quillon"`, `"juniper"` or `"saltmarsh"`.

## Run it

Start the app, then open `http://localhost:8000/` for the chat and `http://localhost:8000/dashboard` for the dashboard:

```bash
python -m app
```

To sign in, use one of your pack's fixture emails. The server prints the one-time code in its own terminal, and the page never shows it. The full list of emails is at `http://localhost:8000/api/signin/options`. Two of each:

| Pack | Email | Role |
|---|---|---|
| Quillon | `adaeze.okoro@ironbridgechambers.example` | customer |
| Quillon | `amara.singh@lindenparklegal.example` | prospect |
| Juniper Lane | `bram.hollis@mailbox.example` | patient |
| Juniper Lane | `pia.strand@mailbox.example` | patient |
| Saltmarsh | `callum.draycott@mail.example` | policyholder |
| Saltmarsh | `priya.anand@mail.example` | policyholder |

Run the harness on your pack. The chapters tell you which command each lab needs:

```bash
python -m harness run --pack quillon --repeat 3
```

`python -m harness` with no command lists every command (`run`, `diff`, `keep`, `revert`, `confirm`, `status` and more).

## Tests and CI

Run every test:

```bash
python -m pytest -q
```

On a fresh template many tests fail with `NotImplementedError`. That is expected: each one passes when you build its part. Run one part's tests with, for example, `pytest challenges/challenge-1-baseline/part-1-setup-and-doctor -q`.

CI (`.github/workflows/ci.yml`) runs the tests with a deterministic stub model, validates your run records and checks for em and en dashes. It needs no secrets. The capstone checker reads that CI run on your final commit.

## Rules

- Every company, person and document here is made up.
- Never commit a key, and never paste one into a chat or a screen share.
- Keep every run record. The harness checks each record against its own digest, so an edited record shows up as `edited`.
