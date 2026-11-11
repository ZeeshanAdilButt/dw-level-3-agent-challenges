"""python -m harness diff <run> [<parent>]: regrade both runs' stored outputs with the current graders (decision B3),
check the runs are comparable (B1), then list the cases that were fixed and broken and give the verdict.

The endpoint is answer success on the eligible questions both runs scored; attacks are a separate endpoint.
Fixed and broken cases go into a two-sided exact sign test at 0.05; ties are dropped.
"""
import argparse
import sys

from . import config, paths, signtest
from .graders import GRADER_VERSION, grade_case
from .records import digest_problems, load_results, load_run, run_path
from .util import read_json, write_json


def selection(rec: dict) -> str:
    """Which cases a run executed: "full", "smoke" or "slice <name>" (from the run's flags)."""
    flags = rec.get("flags") or {}
    if flags.get("slice"):
        return f"slice {flags['slice']}"
    return "smoke" if flags.get("smoke") else "full"


def is_partial(rec: dict) -> bool:
    """A --smoke or --slice run: a subset of the cases, never a full run."""
    return selection(rec) != "full"


def comparable(a: dict, b: dict, one_change: bool = True) -> tuple:
    """(ok, reasons, changed_settings). Same pack, question-set version, case selection and model, and at most one
    setting differs.

    The model (model_path, model, hosted_model together) may itself be the one change (lab 8). Zero differing
    settings is a rerun of the same configuration, which is comparable (noise and confirmation). Two runs over
    different case selections (a smoke or slice run against a full run) are never comparable. With
    one_change=False (confirmation: the best setup against the baseline, which differ in every setting kept in
    labs 2 to 8 by design) any number of settings may differ; pack, question set and selection must still match."""
    reasons = []
    if a.get("kind") != "run" or b.get("kind") != "run":
        reasons.append("both must be full runs (screens are exact and are not compared by verdict)")
    if (a.get("pack") or a["settings"].get("pack")) != (b.get("pack") or b["settings"].get("pack")):
        reasons.append("different packs")
    qa = (a.get("manifest") or {}).get("question_set_version")
    qb = (b.get("manifest") or {}).get("question_set_version")
    if qa != qb:
        reasons.append(f"different question sets ({qa} and {qb})")
    if selection(a) != selection(b):
        reasons.append(f"different case selections ({selection(a)} and {selection(b)})")
    sa, sb = a["settings"], b["settings"]
    diffs = [k for k in config.DEFAULTS if k != "pack" and sa.get(k) != sb.get(k)]
    model = [k for k in diffs if k in config.MODEL_GROUP]
    other = [k for k in diffs if k not in config.MODEL_GROUP]
    if one_change and model and other:
        reasons.append(f"the model and other settings differ ({', '.join(model + other)})")
    elif one_change and len(other) > 1:
        reasons.append(f"{len(other)} settings differ ({', '.join(other)}); exactly one may")
    # Deliberate: a changed setting may change the eligibility mode (tools, rules, topology or a defence switches on
    # "all" in lab 5 and later), and diff and confirm then regrade BOTH runs in "all", so both are scored on the same
    # eligible cases. With no setting changed the modes must agree: a difference means an edited record.
    if (a.get("eligibility") == "all") != (b.get("eligibility") == "all") and not diffs:
        reasons.append("different eligibility modes")
    return not reasons, reasons, diffs


def regrade(run_id: str, mode: str = None) -> dict:
    """{case_id: verdict} from the stored results of a run, graded with today's graders."""
    rec = load_run(run_id)
    bad = digest_problems(run_id, rec)
    if bad:
        raise ValueError("; ".join(bad))
    ctx = read_json(run_path(run_id) / "context.json", {}) or {}
    mode = mode or rec.get("eligibility", "retrieval_only")
    out = {}
    for row in load_results(run_id):
        res = dict(row["result"], case_id=row["case_id"], steps=row["steps"])
        out[row["case_id"]] = grade_case(row["spec"], res, ctx, mode=mode)
    return out


def compare_verdicts(cand: dict, base: dict) -> dict:
    """Fixed and broken cases for the answer-success endpoint (questions) and the security endpoint (attacks)."""
    def endpoint(metric):
        fixed, broken, same, n = [], [], 0, 0
        for cid, v in cand.items():
            b = base.get(cid)
            if b is None or v["m"].get(metric, [0, 0])[1] == 0 or b["m"].get(metric, [0, 0])[1] == 0:
                continue
            n += 1
            c_ok, b_ok = v["m"][metric][0] >= 1, b["m"][metric][0] >= 1
            if c_ok and not b_ok:
                fixed.append(cid)
            elif b_ok and not c_ok:
                broken.append(cid)
            else:
                same += 1
        p = signtest.sign_test(len(fixed), len(broken))
        return {"n": n, "fixed": sorted(fixed), "broken": sorted(broken), "ties": same, "p": p, "p_text": signtest.fmt_p(p),
                "verdict": signtest.verdict(len(fixed), len(broken)),
                "cand_rate": _rate(cand, metric, base), "base_rate": _rate(base, metric, cand)}
    return {"answer_success": endpoint("answer_success"), "security": endpoint("security")}


def _rate(verdicts, metric, other):
    ids = [c for c, v in verdicts.items() if c in other and v["m"].get(metric, [0, 0])[1] and other[c]["m"].get(metric, [0, 0])[1]]
    return (sum(verdicts[c]["m"][metric][0] for c in ids) / len(ids)) if ids else None


def diff_runs(cand_id: str, base_id: str) -> dict:
    cand_rec, base_rec = load_run(cand_id), load_run(base_id)
    ok, reasons, diffs = comparable(cand_rec, base_rec)
    mode = "all" if "all" in (cand_rec.get("eligibility"), base_rec.get("eligibility")) else "retrieval_only"
    cand, base = regrade(cand_id, mode), regrade(base_id, mode)
    cmp = compare_verdicts(cand, base)
    return {"candidate": cand_id, "baseline": base_id, "grader_version": GRADER_VERSION, "comparable": ok,
            "not_comparable_because": reasons, "changed_settings": diffs, "mode": mode, **cmp}


def _line(label, e):
    a = "-" if e["cand_rate"] is None else f"{100 * e['cand_rate']:.1f}%"
    b = "-" if e["base_rate"] is None else f"{100 * e['base_rate']:.1f}%"
    return f"{label}: {a} against {b} on {e['n']} cases both scored"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness diff")
    ap.add_argument("run")
    ap.add_argument("parent", nargs="?")
    a = ap.parse_args(argv)
    try:
        rec = load_run(a.run)
        parent = a.parent or rec.get("parent") or rec.get("from_run")
        if not parent:
            print("error: this run has no parent; name the baseline: diff <run> <baseline>", file=sys.stderr)
            return 2
        d = diff_runs(a.run, parent)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    out = paths.runs_dir() / f"diff-{d['candidate']}-{d['baseline']}.json"
    write_json(out, d)
    print(f"grader version: {d['grader_version']} (both runs regraded from their stored outputs)")
    print(f"candidate {d['candidate']} against baseline {d['baseline']}")
    print("changed settings: " + (", ".join(d["changed_settings"]) or "none (a rerun of the same settings)"))
    if not d["comparable"]:
        print("NOT COMPARABLE: " + "; ".join(d["not_comparable_because"]))
    for label, key in (("answer success (questions)", "answer_success"), ("security pass rate (attacks)", "security")):
        e = d[key]
        print("\n" + _line(label, e))
        print(f"  fixed {len(e['fixed'])}: {' '.join(e['fixed']) or '-'}")
        print(f"  broken {len(e['broken'])}: {' '.join(e['broken']) or '-'}")
        print(f"  ties dropped {e['ties']}; two-sided exact sign test p = {e['p_text']}")
        print(f"  verdict against {d['baseline']}: " + (e["verdict"] if d["comparable"] else "no verdict (the runs are not comparable)"))
    print()
    print(f"wrote {out.relative_to(paths.root()).as_posix()}")
    return 0
