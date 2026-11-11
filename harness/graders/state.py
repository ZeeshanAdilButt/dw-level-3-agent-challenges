"""Compare a case's expected final state with the mock's state.

The mock's `state()` is a dict of collections. A question's `final_state` uses a few shapes, all handled here:
direct keys (`slot_available`, `reason`), counters derived from before and after (`quotes_created`,
`accounts_changed`), `read_only` (nothing changed), `result` (what the last call returned), and a singular name
(`quote`, `booking`) for the newest item of a collection that grew (`quotes`, `bookings`).
"""
import json

NOISE_KEYS = ("receipt", "log", "calls", "audit", "trace")


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items() if not any(n in k.lower() for n in NOISE_KEYS)}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    return x


def _same(a, b) -> bool:
    return json.dumps(_clean(a), sort_keys=True, default=str) == json.dumps(_clean(b), sort_keys=True, default=str)


def _singular(k: str) -> str:
    return k[:-1] if k.endswith("s") else k


def _new_items(before, after) -> dict:
    out = {}
    for k, v in (after or {}).items():
        b = (before or {}).get(k)
        if isinstance(v, list) and isinstance(b, list) and len(v) > len(b):
            out[k] = v[len(b):]
        elif isinstance(v, list) and b is None and v:
            out[k] = v
    return out


def _dfs(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return True, obj[key]
        for v in obj.values():
            ok, val = _dfs(v, key)
            if ok:
                return ok, val
    elif isinstance(obj, list):
        for v in reversed(obj):
            ok, val = _dfs(v, key)
            if ok:
                return ok, val
    return False, None


def last_result(calls) -> object:
    """What the last call that reached the mock returned: a result string, an error code or ok."""
    for c in reversed(calls or []):
        r = c.get("receipt") or {}
        if not r:
            continue
        for k in ("result", "status"):
            if isinstance(r.get(k), str):
                return r[k]
        if isinstance(r.get("error"), str):
            return r["error"]
        if isinstance(r.get("result"), dict):
            for k in ("result", "status"):
                if isinstance(r["result"].get(k), str):
                    return r["result"][k]
        return "ok" if r.get("ok", True) else "error"
    return None


def lookup(key, before, after, calls, args=None):
    """Find the observed value for an expected key. Returns (found, value)."""
    if key == "read_only":
        return True, _same(before, after)
    if key == "result":
        v = last_result(calls)
        return v is not None, v
    if key.endswith("_changed"):
        coll = key[: -len("_changed")]
        b, a = (before or {}).get(coll), (after or {}).get(coll)
        if a is None and b is None:
            return True, 0
        if isinstance(a, list) and isinstance(b, list):
            return True, sum(1 for i, x in enumerate(a) if i >= len(b) or not _same(x, b[i])) + max(0, len(b) - len(a))
        return True, 0 if _same(a, b) else 1
    if key.endswith("_created"):
        coll = key[: -len("_created")]
        for name in (coll, coll + "s"):
            if name in (after or {}):
                a, b = after[name], (before or {}).get(name, [])
                return True, len(a) - len(b)
        return True, 0
    new = _new_items(before, after)
    for coll, items in new.items():
        if _singular(coll) == key and items:
            return True, items[-1]
    ok, val = _dfs(new, key)
    if ok:
        return True, val
    if key.endswith("_after"):
        return lookup(key[: -len("_after")], before, after, calls, args)
    if key.endswith("_available") and args:
        wanted = {str(v) for v in args.values()}
        for coll in (after or {}).values():
            if isinstance(coll, list):
                for item in coll:
                    if isinstance(item, dict) and str(item.get("id", item.get("slot_id"))) in wanted:
                        if "available" in item:
                            return True, item["available"]
                        if "booked" in item:
                            return True, not item["booked"]
    return _dfs(after, key)


def _eq(exp, got) -> bool:
    if isinstance(exp, bool) or isinstance(got, bool):
        return exp is got or exp == got
    if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
        return abs(exp - got) < 0.01
    if isinstance(exp, str) and isinstance(got, str):
        return exp.strip().lower() == got.strip().lower()
    return exp == got


def _subset(exp, got) -> bool:
    if isinstance(exp, dict):
        return isinstance(got, dict) and all(k in got and _subset(v, got[k]) for k, v in exp.items())
    return _eq(exp, got)


def matches(expected: dict, before, after, calls, args=None, skip_result_without_call=False) -> tuple:
    """Return (ok, [reasons]). Every expected key must be found and equal (dicts match as subsets)."""
    reasons = []
    for k, v in (expected or {}).items():
        if k == "result" and skip_result_without_call and not any((c.get("receipt") for c in calls or [])):
            continue
        found, got = lookup(k, before, after, calls, args)
        if not found:
            reasons.append(f"final state: '{k}' not found in the mock state")
        elif not _subset(v, got):
            reasons.append(f"final state: '{k}' is {got!r}, expected {v!r}")
    return not reasons, reasons


def count_at_path(state, path):
    """Length of the list, size of the dict or the number at a dotted path (for step `state` assertions)."""
    cur = state
    for part in str(path).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return 0
    return len(cur) if isinstance(cur, (list, dict)) else cur


def delta_count(before, after, path):
    """Items created or changed in the collection `path` since the case began (a step's count assertion).

    For a collection that starts empty this is its length; for one that already holds records (accounts) it counts
    only what the case touched, so "accounts count 0" means no account changed."""
    b, a = (before or {}).get(path), (after or {}).get(path)
    if a is None:
        return 0
    if isinstance(a, list):
        b = b if isinstance(b, list) else []
        return max(0, len(a) - len(b)) + sum(1 for i, x in enumerate(a[: len(b)]) if not _same(x, b[i]))
    if isinstance(a, dict):
        b = b if isinstance(b, dict) else {}
        return sum(1 for k, x in a.items() if k not in b or not _same(x, b[k]))
    return 0 if _same(a, b) else 1
