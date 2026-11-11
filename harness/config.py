"""Settings resolution: parent run first, then --set, printed before anything runs.

Uses app.settings.load_settings when it exists (the app core builder owns it); otherwise a small
resolver with the same rules, so the harness works before the core does.
"""
import re
import tomllib

from . import paths
from .util import read_json

DEFAULTS = {
    "pack": "quillon", "model_path": "local", "model": "qwen3:4b-instruct", "hosted_model": "",
    "embed_model": "nomic-embed-text", "temperature": 0.2, "top_k": 5, "chunker": "fixed", "chunk_size": 400,
    "overlap": 0, "retriever": "bm25", "context": "none", "neighbours_n": 1, "context_token_limit": 3000,
    "authority_rule": "off", "tools": "off", "rules": "off", "topology": "single", "defences": [],
    "trace_steps": "off", "region": "Port Avery", "emergency_number": "112",
}
CHOICES = {
    "model_path": {"local", "hosted", "stub"}, "chunker": {"fixed", "heading"},
    "retriever": {"bm25", "trigram", "vector", "hybrid"},
    "context": {"none", "neighbours", "section_parent", "link_hop"},
    "authority_rule": {"off", "on"}, "tools": {"off", "on"}, "rules": {"off", "on"},
    "topology": {"single", "router_specialists", "router_specialists_reviewer"}, "trace_steps": {"off", "on"},
}
# Which lab a setting belongs to (blueprint table); the gate uses it to find a lab's runs.
LAB_OF = {"model_path": 8, "top_k": 1, "chunker": 2, "chunk_size": 2, "overlap": 2, "retriever": 3,
          "context": 4, "neighbours_n": 4, "context_token_limit": 4, "authority_rule": 4, "tools": 5, "rules": 5,
          "topology": 6, "defences": 7, "trace_steps": 8}
MODEL_GROUP = ("model_path", "model", "hosted_model")


class SettingsError(ValueError):
    pass


def coerce(key, raw):
    """Turn a --set string into the type of the default."""
    if key not in DEFAULTS:
        raise SettingsError(f"unknown setting '{key}'. Known: {', '.join(sorted(DEFAULTS))}")
    if not isinstance(raw, str):
        return raw
    d = DEFAULTS[key]
    try:
        if isinstance(d, bool):
            return raw.lower() in ("1", "true", "yes", "on")
        if isinstance(d, int):
            return int(raw)
        if isinstance(d, float):
            return float(raw)
        if isinstance(d, list):
            return [x.strip() for x in re.split(r"[,\s]+", raw) if x.strip()]
    except ValueError:
        raise SettingsError(f"setting '{key}' needs a {type(d).__name__}, got '{raw}'")
    return raw


def parse_sets(pairs) -> dict:
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise SettingsError(f"--set needs key=value, got '{p}'")
        k, v = p.split("=", 1)
        out[k.strip()] = coerce(k.strip(), v.strip())
    return out


def flatten_toml(data: dict) -> dict:
    flat = {}
    for k, v in data.items():
        if isinstance(v, dict):
            flat.update(flatten_toml(v))
        else:
            flat[k] = v
    return flat


DEFENCES = ("access", "marking", "output_check")
MINIMUM = {"top_k": 1, "chunk_size": 1, "overlap": 0, "neighbours_n": 0, "context_token_limit": 1}


def validate(s: dict) -> dict:
    """The same checks as app/settings.py validate, for when the core is not importable yet."""
    for k, low in MINIMUM.items():
        if isinstance(s[k], bool) or not isinstance(s[k], int):
            raise SettingsError(f"setting '{k}' must be an integer, got {s[k]!r}")
        if s[k] < low:
            raise SettingsError(f"setting '{k}' must be at least {low}, got {s[k]}")
    if not (0 <= s["overlap"] < s["chunk_size"]):
        raise SettingsError(f"overlap must satisfy 0 <= overlap < chunk_size (got {s['overlap']}, {s['chunk_size']})")
    for k, allowed in CHOICES.items():
        if s[k] not in allowed:
            raise SettingsError(f"setting '{k}' must be one of {sorted(allowed)}, got '{s[k]}'")
    t = s["temperature"]
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 <= t <= 2:
        raise SettingsError(f"temperature must be a number from 0 to 2, got {t!r}")
    bad = [d for d in (s["defences"] or []) if d not in DEFENCES]
    if bad:
        raise SettingsError(f"unknown defence '{bad[0]}'; known: {', '.join(DEFENCES)}")
    if s["model_path"] == "hosted" and not s["hosted_model"]:
        raise SettingsError("model_path=hosted needs hosted_model")
    return s


def _fallback_load(overrides, base):
    s = dict(DEFAULTS)
    toml = paths.root() / "config" / "settings.toml"
    if toml.exists():
        s.update({k: v for k, v in flatten_toml(tomllib.loads(toml.read_text(encoding="utf-8"))).items()
                  if k in DEFAULTS})
    s.update({k: v for k, v in (base or {}).items() if k in DEFAULTS})
    s.update(overrides or {})
    return validate(s)


def load_settings(overrides=None, base=None) -> dict:
    try:
        from app.settings import load_settings as core_load  # type: ignore
    except Exception:
        return _fallback_load(overrides, base)
    return core_load(overrides=overrides, base=base)


def kept_run_id():
    kept = read_json(paths.runs_dir() / "kept.json")
    return kept.get("run_id") if kept else None


def run_settings(run_id: str):
    rec = read_json(paths.runs_dir() / run_id / "run.json")
    if not rec:
        raise SettingsError(f"no run record for '{run_id}' under runs/")
    return rec["settings"]


def resolve(pack=None, parent=None, from_run=None, sets=None, use_default_parent=True):
    """Return (settings, parent_id, change). Order: defaults and toml, the parent's settings, then --set."""
    sets = dict(sets or {})
    if pack:
        sets.setdefault("pack", pack)
    source = parent or from_run
    if source is None and use_default_parent:
        source = kept_run_id()
        parent = source
    base = run_settings(source) if source else None
    settings = load_settings(overrides=sets, base=base)
    change = None
    if base is not None:
        change = {k: [base.get(k), settings[k]] for k in settings if k in DEFAULTS and base.get(k) != settings[k]}
    return settings, parent, change


def describe(settings: dict, change=None) -> str:
    lines = ["resolved settings:"]
    lines += [f"  {k} = {settings[k]!r}" for k in DEFAULTS if k in settings]
    if change is not None:
        lines.append("change from parent: " + (", ".join(f"{k}: {a!r} -> {b!r}" for k, (a, b) in change.items())
                                              or "none"))
    return "\n".join(lines)


def effective_model(s: dict) -> str:
    return f"{s.get('model_path')}:{s.get('hosted_model') if s.get('model_path') == 'hosted' else s.get('model')}"
