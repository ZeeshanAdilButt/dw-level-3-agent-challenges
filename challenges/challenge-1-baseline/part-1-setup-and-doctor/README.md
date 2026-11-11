# Challenge 1, part 1: setup and the doctor

You get the project running on your laptop, pass the doctor, pick one company, and find out which model path you are on. Run every command from the repository root. All companies, documents, accounts and patients in this course are synthetic. A real clinic would need clinical and legal review that this course does not give.

## The idea, from zero

The agent you build has two kinds of model behind it. A **chat model** reads the question and the documents and writes the answer. An **embedding model** turns text into a list of numbers, so that lab 3 can search by meaning. Both can run on your own laptop through a free program called Ollama (the **local path**), or the chat model can run on a paid hosted service (the **hosted path**). Embeddings stay local on both paths.

Why a doctor? A small model on a slow laptop can take half a minute per answer. A full run asks about 150 questions, so a slow laptop makes every lab wait. The doctor runs the six checks the course needs and then times five real chat calls. The rule is one line: a median call time of 8 seconds or less picks the local path, and a longer median picks the hosted path ([`MEDIAN_LIMIT_S`](../../../tools/doctor.py#L27), [`choose_path`](../../../tools/doctor.py#L123-L128)). The median is the middle of the five sorted times, so one slow first call (it includes loading the model) does not decide the path. The hardware does not decide it either: only the timing does.

## Step 1: get the project (12 min)

1. Create your repository from the template (the public export, which holds no hidden questions), clone it, make a virtual environment and install the requirements.
2. Create a file called `.gitignore` if the clone has none, and put the line `.env` in it **before your first commit**. A `.env` file is where you keep keys. The course never asks you to paste a key into chat, into a commit or on screen.
3. Make the first commit.

## Step 2: the doctor and the models (15 min)

Install Ollama, then start the downloads first because they take the longest:

```bash
ollama pull qwen3:4b-instruct
ollama pull nomic-embed-text
```

The two names are in [`LOCAL_MODELS`](../../../tools/doctor.py#L30). The download is about 2.8 GB in all. While it runs, do step 3.

Then run:

```bash
python tools/doctor.py
```

Read it line by line. Each line starts with `[ok  ]`, `[FAIL]` or `[warn]`:

| Line | What it checks | Where |
|---|---|---|
| Python | version 3.11 or newer | [`check_python`](../../../tools/doctor.py#L50-L53) |
| SQLite FTS5 and bm25() | the keyword search you ship from lab 1 works in this Python | [`check_fts5`](../../../tools/doctor.py#L56-L65) |
| Git | Git is installed, because a run starts only from a committed tree | [`check_git`](../../../tools/doctor.py#L68-L73) |
| Disk space | about 10 GB free, a warning only | [`check_disk`](../../../tools/doctor.py#L76-L79) |
| Ollama and Models | Ollama answers and both models are present | [`check_ollama`](../../../tools/doctor.py#L99-L107) |

Then it prints `Seconds per call:` for five timed calls ([`time_calls`](../../../tools/doctor.py#L110-L120)) and one verdict line, for example `Median 4.2 s against the 8 s limit. Use the LOCAL path`. Where each number comes from: the five times are measured on your machine, the median is [`statistics.median`](../../../tools/doctor.py#L119-L124) of them, and 8 is the constant above.

A miss is not a failure. If the models are missing or the median is over 8 seconds, the doctor sends you to the hosted path and tells you what to set. The hosted path reads two environment variables, `DW_HOSTED_BASE_URL` and `DW_HOSTED_API_KEY` ([`app/model.py`](../../../app/model.py#L72-L77)). Ask your instructor whether hosted credit is available. A whole course on the hosted path is about one to two dollars at list price. Keep the key in `.env` and load it into your terminal yourself; never commit it, and close `.env` before any screen share.

Reference laptop, for comparison (yours may differ): the median call took 2500 milliseconds with the GPU and 5500 milliseconds on the CPU only. The reference output was:

```
[ok  ] Python: 3.12.10
[ok  ] SQLite FTS5 and bm25(): SQLite 3.49.1, bm25 score -0.000
[ok  ] Git: git version 2.51.0.windows.1
[ok  ] Disk space: 18.2 GB free here (models and runs need about 10 GB)
[ok  ] Ollama: reachable at http://localhost:11434
[ok  ] Models: both present
Timing 5 chat calls on qwen3:4b-instruct (the first one loads the model) ...
Seconds per call: 16.7, 2.2, 2.1, 2.2, 2.1
Median 2.2 s against the 8 s limit. Use the LOCAL path (model_path = "local").
Wrote doctor.json.
Required checks passed.
```

## Step 3: pick a company and prove it (13 min)

Read `eval/questions.md` in each pack (`packs/quillon/`, `packs/juniper/`, `packs/saltmarsh/`) and choose one company. You keep it for the whole course.

| Company | Pack folder | Documents | First question |
|---|---|---|---|
| Quillon (contract software) | `packs/quillon/` | 148 | q-001 |
| Juniper Lane Clinic | `packs/juniper/` | 150 | q-001 |
| Saltmarsh Mutual | `packs/saltmarsh/` | 148 | q-001 |

Write your choice into [`config/settings.toml`](../../../config/settings.toml#L9): `pack = "<your-pack>"` and, two lines below it, `model_path = "local"` or `"hosted"` as the doctor said ([line 11](../../../config/settings.toml#L11)). On the hosted path, also fill `hosted_model` (a few lines further down) with a name from `config/prices.toml`, for example `claude-haiku-5-5`; the app refuses to start on `hosted` without it.

Write `results.md` in this folder: paste the whole doctor output, then add two lines of your own.

```
company: <quillon, juniper or saltmarsh>
model path: <local or hosted>
```

## The tests

```bash
python -m pytest challenges/challenge-1-baseline/part-1-setup-and-doctor -q
```

Invariant tests, which pass on the starter: `test_settings_parse` (the settings file parses and holds a valid pack and path), `test_doctor_rule` (6 seconds is local, 8.0 is still local, 8.1 and no timings are hosted), `test_model_names`, `test_the_receipt_checker_on_fixed_receipts`.

Acceptance test, which fails on the starter with `AssertionError: results.md has no doctor receipt`: `test_doctor_receipt`. It passes when `results.md` holds the passing Python, SQLite FTS5 and Git lines, the median line (or the doctor's hosted-path line), a `company:` that equals the `pack` in your settings, a `model path:` that equals your `model_path`, and `.env` is a line of `.gitignore`. The tests use fixed inputs and your own files. They never compare your numbers with the reference.

Commit `results.md`, `config/settings.toml` and `.gitignore`, and push.

## If something looks wrong

- **`SQLite FTS5` fails.** Your Python was built without FTS5. Install a Python from python.org or use `pyenv`, then repeat the doctor.
- **`Ollama` is not reachable.** Start it with `ollama serve`. On a laptop the Ollama app does this at login.
- **The first call is 30 seconds and the others are 4.** That is the model loading. The median ignores it.
- **The median is 9 seconds and you have no GPU.** The hosted path is the right answer. It is not a failure.
