"""python -m harness gate <lab> [--part N]: the gate receipt.

Checks, from the learner's own records only (never the reference numbers): the work is committed, the prediction
was committed before the lab's first screen or run, the screens and the candidate run share every setting but the
lab's own, the candidate is comparable with its parent, the decision (keep or revert) is recorded, run records are
valid, and results.md exists and cites only run ids that exist. It warns when code outside the lab's declared
files changed. With --part N it checks that part's folder (README.md, results.md, a test).
"""
import argparse
import fnmatch
import re
import sys
from datetime import datetime

from . import config, paths
from .diff import comparable, is_partial
from .graders import GRADER_VERSION
from .records import all_runs, kept, load_run
from .run import dirty_paths
from .schema import validate_run_dir
from .util import git, now_iso, read_json, sha

COMMON = ["config/*", "runs/*", "predictions/*", "LAB-LOG.md", "REPORT.md", "challenges/*", "tests/*", "dashboard/*",
          "app/core.py", "app/settings.py", ".github/*"]
DECLARED = {
    1: ["harness/graders/fact.py", "harness/graders/citation.py", "harness/graders/recall.py"],
    2: ["app/retrieval/chunkers.py", "harness/graders/fact.py"],
    3: ["app/retrieval/*"],
    4: ["app/context.py", "app/prompts/*", "app/retrieval/*"],
    5: ["app/tools/*", "app/rules/*", "app/prompts/*", "harness/graders/tool.py", "harness/graders/handoff.py", "app/idempotency.py"],
    6: ["app/agents/*", "app/prompts/*"],
    7: ["app/security/*", "app/rules/*", "app/prompts/*"],
    8: ["app/model.py", "app/trace.py", "app/prompts/*"],
    9: ["*"],
}


class Receipt:
    def __init__(self):
        self.rows = []

    def add(self, status, name, detail=""):
        self.rows.append((status, name, detail))

    @property
    def failed(self):
        return any(s == "FAIL" for s, _, _ in self.rows)


def confirmed_run_ids() -> set:
    """Every run named on either side of a runs/confirm-<id>.json."""
    out = set()
    d = paths.runs_dir()
    for f in sorted(d.glob("confirm-*.json")) if d.exists() else []:
        art = read_json(f, {}) or {}
        for side in ("best", "baseline"):
            out |= set(((art.get(side) or {}).get("runs")) or [])
    return out


def lab_records(lab: int) -> list:
    """Records that belong to a lab: those that changed (or named with --set) one of the lab's settings.

    Lab 1 owns the baseline and its reruns with no change (the noise floor), also when a run was kept before the
    other reruns started and so became their parent. Lab 9 (the capstone) owns the confirmation runs: those named
    in a runs/confirm-<id>.json and the --from-run reruns."""
    recs = [r for r in all_runs() if r.get("kind") in ("run", "screen")]
    confirmed = confirmed_run_ids() if lab == 9 else set()

    def keys_of(rec):
        keys = set((rec.get("change") or {}).keys()) | set(rec.get("explicit_sets") or [])
        keys.discard("pack")
        return keys

    baselines = [r["settings"] for r in recs if r["kind"] == "run" and not keys_of(r) and r.get("parent") is None
                 and not r.get("from_run")]
    out = []
    for rec in recs:
        keys = keys_of(rec)
        if lab == 9:
            if rec.get("kind") == "run" and (rec["run_id"] in confirmed or rec.get("from_run")):
                out.append(rec)
        elif not keys:
            if lab == 1 and rec.get("kind") == "run" and not rec.get("from_run") \
                    and (rec.get("parent") is None or rec.get("settings") in baselines):
                out.append(rec)
        elif any(config.LAB_OF.get(k) == lab for k in keys):
            out.append(rec)       # a record that also changes another lab's setting is kept, so the check below can flag it
    return sorted(out, key=lambda r: r.get("started_at", ""))


def _t(s):
    return datetime.fromisoformat(s)


def prediction_files(lab: int) -> list:
    d = paths.root() / "predictions"
    if not d.exists():
        return []
    pat = re.compile(rf"(?<!\d){lab}(?!\d)")
    return [p for p in sorted(d.iterdir()) if p.is_file() and pat.search(p.name)]


PREDICTION_WORDS = {
    "context": "context", "authority_rule": "authority", "tools": "tools", "rules": "rules", "trace_steps": "trace",
    "model_path": "switch", "model": "switch", "hosted_model": "switch",
}
TOPOLOGY_WORDS = {"router_specialists": "teams", "router_specialists_reviewer": "reviewer"}
DEFENCE_WORDS = {"access": "access", "marking": "marking", "output_check": "leak"}


def prediction_words(rec: dict) -> list:
    """Words that tell which prediction file belongs to a run, from what the run changed (lab 6: team or reviewer;
    lab 7: the defence it added; lab 4, 5 and 8: the setting it switched)."""
    change = rec.get("change") or {}
    named = set(change) | set(rec.get("explicit_sets") or [])
    settings = rec.get("settings") or {}
    words = []
    if "topology" in named and settings.get("topology") in TOPOLOGY_WORDS:
        words.append(TOPOLOGY_WORDS[settings["topology"]])
    if "defences" in named:
        old = set((change.get("defences") or [[], []])[0] or [])
        words += [DEFENCE_WORDS[d] for d in settings.get("defences") or [] if d not in old and d in DEFENCE_WORDS]
    words += [PREDICTION_WORDS[k] for k in sorted(named) if k in PREDICTION_WORDS]
    return words


def prediction_for(rec: dict, files: list, times: dict = None):
    """The prediction file of this run: the one whose name holds the word of its change.

    A run whose change names no file (lab 4 `neighbours_n`, a smoke run, a setting the words do not know) belongs to the
    prediction the learner had most recently committed when it started, so a correct learner who writes the part 2
    prediction after part 1's runs is not judged against it. With no such file it falls back to the earliest one."""
    for word in prediction_words(rec):
        for f in files:
            if word in f.name.lower():
                return f
    if not files:
        return None
    times = times or {}
    before = [f for f in files if times.get(f) and _t(times[f]) <= _t(rec["started_at"])]
    if before:
        return max(before, key=lambda f: _t(times[f]))
    dated = [f for f in files if times.get(f)]
    return min(dated, key=lambda f: _t(times[f])) if dated else files[0]


def first_commit_time(path):
    rel = path.relative_to(paths.root()).as_posix()
    out = git("log", "--diff-filter=A", "--format=%cI", "--", rel)
    return out.splitlines()[-1] if out else None


def commits_of(path) -> list:
    """[(commit, committed_at)] of every commit that touched the file, newest first."""
    rel = path.relative_to(paths.root()).as_posix()
    out = git("log", "--format=%H|%cI", "--", rel)
    return [tuple(line.split("|", 1)) for line in (out or "").splitlines() if "|" in line]


def prediction_text_at(path, when: str):
    """(text of the file as last committed at or before `when`, commits that touched it after `when`)."""
    commits = commits_of(path)
    before = [c for c, at in commits if _t(at) <= _t(when)]
    after = [c for c, at in commits if _t(at) > _t(when)]
    if not before:
        return None, after
    rel = path.relative_to(paths.root()).as_posix()
    return git("show", f"{before[0]}:{rel}") or "", after


def check(lab: int, part, r: Receipt):
    bad = dirty_paths()
    r.add("FAIL" if bad else "PASS", "work is committed", ("uncommitted: " + ", ".join(bad[:5])) if bad else "")
    recs = lab_records(lab)
    runs = [x for x in recs if x["kind"] == "run" and x.get("status") == "complete" and not is_partial(x)]   # smoke and slice runs are not candidates
    screens = [x for x in recs if x["kind"] == "screen"]
    if lab == 9:
        confirms = sorted(p.name for p in paths.runs_dir().glob("confirm-*.json")) if paths.runs_dir().exists() else []
        r.add("PASS" if confirms else "FAIL", "confirmation artifact", ", ".join(confirms) or "no runs/confirm-<id>.json yet")
    else:
        r.add("PASS" if runs else "FAIL", f"a complete full run for lab {lab}", ", ".join(x["run_id"] for x in runs) or "none found")
    if recs:
        files = prediction_files(lab)
        if not files:
            r.add("FAIL", "prediction file", f"no predictions/ file for lab {lab}")
        else:
            times = {f: first_commit_time(f) for f in files}
            own = {}                       # each run is matched with its own prediction file (lab6-reviewer, not lab6-teams)
            for rec in recs:
                own.setdefault(prediction_for(rec, files, times), rec)
            for pf, first in own.items():
                t_pred = times.get(pf)
                if t_pred is None:
                    r.add("FAIL", "prediction committed", f"{pf.name} is not committed")
                elif _t(t_pred) < _t(first["started_at"]) and first.get("prediction_commit"):
                    text, later = prediction_text_at(pf, first["started_at"])
                    if not (text or "").strip():
                        r.add("FAIL", "prediction before the first record", f"{pf.name} was empty when {first['run_id']} "
                              f"started {first['started_at']}; a prediction is written before the record")
                        continue
                    r.add("PASS", "prediction before the first record", f"{pf.name} committed {t_pred}, first {first['kind']} "
                          f"{first['run_id']} started {first['started_at']}")
                    if later:
                        r.add("WARN", "prediction unchanged after the first record",
                              f"{pf.name} changed in {len(later)} commit(s) after {first['run_id']} started; the version "
                              "committed before it is the prediction")
                else:
                    r.add("FAIL", "prediction before the first record", f"{pf.name} was committed {t_pred}, "
                          f"after (or without being seen by) {first['run_id']} started {first['started_at']}")
    keys = {k for k, v in config.LAB_OF.items() if v == lab}
    group = screens + runs
    if lab != 9 and len(group) > 1:            # the capstone's best and baseline differ in many settings by design
        others = {tuple(sorted((k, str(v)) for k, v in x["settings"].items() if k not in keys)) for x in group}
        r.add("PASS" if len(others) == 1 else "FAIL", f"screens and runs share every setting but {'/'.join(sorted(keys))}",
              "" if len(others) == 1 else f"{len(others)} different settings groups among " + ", ".join(x["run_id"] for x in group))
    if lab == 3 and screens:
        have = {x["settings"]["retriever"] for x in screens}
        need = {"bm25", "trigram", "vector", "hybrid"}
        r.add("PASS" if need <= have else "FAIL", "all four retrievers screened", "missing: " + ", ".join(sorted(need - have)) if need - have else "")
    for x in runs:
        if x.get("parent"):
            try:
                ok, why, _ = comparable(x, load_run(x["parent"]))
                r.add("PASS" if ok else "FAIL", f"{x['run_id']} comparable with parent {x['parent']}", "; ".join(why))
            except FileNotFoundError:
                r.add("FAIL", f"{x['run_id']} parent exists", f"no record for {x['parent']}")
            c = (x.get("manifest") or {}).get("code") or {}
            pc = ((load_run(x["parent"]).get("manifest") or {}).get("code") or {}).get("commit") if x.get("parent") else None
            if c.get("commit") and pc and c["commit"] != pc:
                changed = (git("diff", "--name-only", pc, c["commit"]) or "").splitlines()
                allowed = COMMON + DECLARED.get(lab, [])
                stray = [f for f in changed if not any(fnmatch.fnmatch(f, g) for g in allowed)]
                r.add("WARN" if stray else "PASS", "code changes inside the lab's declared files", ", ".join(stray[:6]))
    k = kept()
    decided = {d["run"] for d in k.get("decisions") or []} | {h["run"] for h in k.get("history") or []}
    needing = [x for x in runs if needs_decision(x, lab)]
    later = decision_comes_later(lab, part)
    for x in needing:
        if x["run_id"] in decided:
            r.add("PASS", f"{x['run_id']} has a keep or revert decision")
        elif later and x is needing[-1]:
            r.add("WARN", f"{x['run_id']} has a keep or revert decision", f"not yet: {later} asks for it")
        else:
            r.add("FAIL", f"{x['run_id']} has a keep or revert decision", "run `harness keep` or `harness revert` to complete the lab")
    log = paths.root() / "LAB-LOG.md"
    log_text = log.read_text(encoding="utf-8") if log.exists() else ""
    for x in runs:
        if x["run_id"] in decided:
            r.add("PASS" if x["run_id"] in log_text else "FAIL", f"LAB-LOG.md has an entry for the decision on {x['run_id']}",
                  "" if x["run_id"] in log_text else "write the lab's entry in LAB-LOG.md and name the run")
    errs = []
    for x in recs:
        errs += validate_run_dir(x["run_id"])
    r.add("FAIL" if errs else "PASS", "run records are valid", "; ".join(errs[:3]))
    if lab == 1 and runs:
        same = {}
        for x in runs:
            same.setdefault(str(sorted(x["settings"].items())), []).append(x["run_id"])
        biggest = max(same.values(), key=len)
        r.add("PASS" if len(biggest) >= 3 else "WARN", "noise floor: three runs of the same settings", f"{len(biggest)} found")
    check_results(lab, part, r)


def needs_decision(rec: dict, lab: int) -> bool:
    """Every candidate full run of labs 2 to 8 is kept or reverted. In lab 1 only a run that changed a setting is
    (the baseline and its noise reruns are not candidates); the capstone's confirmation runs are never kept."""
    if lab == 9:
        return False
    if lab == 1:
        return bool((rec.get("change") or {}) or rec.get("explicit_sets"))
    return True


ASKS_DECISION = re.compile(r"harness (keep|revert)\b")


def decision_comes_later(lab: int, part):
    """The README that asks for the decision on the lab's last run, when that is a later part than the one gated:
    a later part of the same lab (with --part), or a sentence of the next lab's first part that names this lab
    (9.1 keeps or reverts the model switch started in 8.5). None when the decision is due now."""
    numbered = []
    for p in part_dirs(lab):
        m = re.match(r"part-(\d+)", p.name)
        if m:
            numbered.append((int(m.group(1)), p))
    if part is not None:
        for n, p in numbered:
            readme = p / "README.md"
            if n > part and readme.exists() and ASKS_DECISION.search(readme.read_text(encoding="utf-8")):
                return f"part {n} ({p.parent.name}/{p.name}/README.md)"
        if numbered and part < max(n for n, _ in numbered):
            return None
    for p in part_dirs(lab + 1)[:1]:
        readme = p / "README.md"
        text = readme.read_text(encoding="utf-8") if readme.exists() else ""
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if ASKS_DECISION.search(sentence) and re.search(rf"(?<![\d.]){lab}\.\d|\blab {lab}\b", sentence, re.IGNORECASE):
                return f"the next lab's first part ({p.parent.name}/{p.name}/README.md)"
    return None


def part_dirs(lab: int):
    base = paths.root() / "challenges"
    out = []
    for c in sorted(base.glob(f"challenge-{lab}-*")) if base.exists() else []:
        out += sorted(p for p in c.glob("part-*") if p.is_dir())
    return out


# Which parts ask the learner to write results.md. Detected from the part's README text: a sentence (a dot inside a file name is not a sentence end) where write, save or
# paste comes before results.md ("Write `results.md` in this folder", "Save it in this part's `results.md`"). A README
# that only mentions the file in passing (the gate description in lab 3 part 2, lab 4 part 2) does not ask for it.
# A results.md that exists is still checked for run ids in every part; it is only required where the README asks.
ASKS_RESULTS = re.compile(r"\b(write|save|paste)\b(?:[^.\n]|\.(?=\w)){0,200}results\.md", re.IGNORECASE)


def asks_for_results(part_dir) -> bool:
    readme = part_dir / "README.md"
    if not readme.exists():
        return False
    return bool(ASKS_RESULTS.search(readme.read_text(encoding="utf-8")))


def check_results(lab, part, r: Receipt):
    parts = part_dirs(lab)
    if part is not None:
        parts = [p for p in parts if re.match(rf"part-{part}(-|$)", p.name)]
        if not parts:
            r.add("FAIL", f"part {part} folder", f"no challenges/challenge-{lab}-*/part-{part}-*/ folder")
            return
    elif not parts:
        r.add("WARN", "part folders", f"no challenges/challenge-{lab}-*/part-* folders")
        return
    run_ids = {x["run_id"] for x in all_runs()}
    for p in parts:
        rel = p.relative_to(paths.root()).as_posix()
        res = p / "results.md"
        missing = [n for n in ("README.md",) if not (p / n).exists()]
        if part is not None and not list(p.glob("test*.py")) and not list(p.glob("tests/*.py")):
            missing.append("a test (test_*.py)")
        if missing:
            r.add("FAIL", f"{rel} files", "missing " + ", ".join(missing))
        has = res.exists() and res.read_text(encoding="utf-8").strip()
        if not has:
            if asks_for_results(p):
                r.add("FAIL", f"{rel}/results.md", "missing or empty (the README asks you to write it)")
            continue
        cited = set(re.findall(r"\b([rs]\d{3,})\b", res.read_text(encoding="utf-8")))
        unknown = sorted(cited - run_ids)
        r.add("FAIL" if unknown else "PASS", f"{rel}/results.md cites only your own runs", ("no run record for " + ", ".join(unknown)) if unknown else "")


def parse_lab(text):
    t = str(text).strip().lower()
    if t == "capstone":
        return 9
    return int(t) if t.isdigit() and 1 <= int(t) <= 9 else None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness gate")
    ap.add_argument("lab", help="1 to 9, or capstone (the same checks as 9)")
    ap.add_argument("--part", type=int)
    a = ap.parse_args(argv)
    a.lab = parse_lab(a.lab)
    if a.lab is None:
        print("error: lab must be 1 to 9 or capstone", file=sys.stderr)
        return 2
    r = Receipt()
    check(a.lab, a.part, r)
    width = max(len(n) for _, n, _ in r.rows)
    print(f"GATE lab {a.lab}" + (f" part {a.part}" if a.part else ""))
    for s, n, d in r.rows:
        print(f"  {s:4s} {n:{width}s}  {d}")
    npass = sum(s == "PASS" for s, _, _ in r.rows)
    nwarn = sum(s == "WARN" for s, _, _ in r.rows)
    nfail = sum(s == "FAIL" for s, _, _ in r.rows)
    result = "FAIL" if nfail else "PASS"
    body = f"lab {a.lab} part {a.part} {result} {npass} {nwarn} {nfail} {git('rev-parse', 'HEAD')} {GRADER_VERSION}"
    print(f"\nreceipt: lab {a.lab}{f' part {a.part}' if a.part else ''} {result} ({npass} passed, {nwarn} warnings, {nfail} failed)")
    print(f"  at {now_iso()}  commit {(git('rev-parse', '--short', 'HEAD') or 'none')}  grader {GRADER_VERSION}")
    print(f"  receipt id {sha(body)[:12]}")
    return 1 if r.failed else 0
