"""Settings: defaults, the optional config/settings.toml, a parent run's settings, then overrides; validated."""
from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULTS: dict = {
    "pack": "quillon",
    "model_path": "local",
    "model": "qwen3:4b-instruct",
    "hosted_model": "",
    "embed_model": "nomic-embed-text",
    "temperature": 0.2,
    "top_k": 5,
    "chunker": "fixed",
    "chunk_size": 400,
    "overlap": 0,
    "retriever": "bm25",
    "context": "none",
    "neighbours_n": 1,
    "context_token_limit": 3000,
    "authority_rule": "off",
    "tools": "off",
    "rules": "off",
    "topology": "single",
    "defences": [],
    "trace_steps": "off",
    "region": "Port Avery",
    "emergency_number": "112",
}

COMPANIES = ("quillon", "juniper", "saltmarsh")
PACK_SUFFIXES = ("-mine", "-practice")      # a learner's own copy (<co>-mine) or a small practice copy (<co>-practice)


def company_of(pack: str) -> str:
    """The company a pack folder belongs to: quillon-mine is Quillon's rules and tools on the learner's own documents."""
    for suffix in PACK_SUFFIXES:
        if isinstance(pack, str) and pack.endswith(suffix) and pack[: -len(suffix)] in COMPANIES:
            return pack[: -len(suffix)]
    return pack


CHOICES = {
    "pack": COMPANIES + tuple(c + s for c in COMPANIES for s in PACK_SUFFIXES),
    "model_path": ("local", "hosted", "stub"),
    "chunker": ("fixed", "heading"),
    "retriever": ("bm25", "trigram", "vector", "hybrid"),
    "context": ("none", "neighbours", "section_parent", "link_hop"),
    "authority_rule": ("off", "on"),
    "tools": ("off", "on"),
    "rules": ("off", "on"),
    "trace_steps": ("off", "on"),
    "topology": ("single", "router_specialists", "router_specialists_reviewer"),
}
DEFENCES = ("access", "marking", "output_check")
INT_KEYS = ("top_k", "chunk_size", "overlap", "neighbours_n", "context_token_limit")


class SettingsError(ValueError):
    pass


def _coerce(key, value):
    if key in INT_KEYS and isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise SettingsError(f"{key} must be an integer, got {value!r}")
    if key == "temperature" and isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            raise SettingsError(f"temperature must be a number, got {value!r}")
    if key in CHOICES and "on" in CHOICES[key] and isinstance(value, bool):
        return "on" if value else "off"
    if key == "defences":
        if isinstance(value, str):
            value = [v.strip() for v in value.split(",") if v.strip()]
        return list(value or [])
    if key in ("region", "emergency_number") and value is None:
        return ""
    if key == "emergency_number":
        return str(value)
    return value


def validate(settings: dict) -> dict:
    """Return a validated copy. Raises SettingsError on an unknown key or value."""
    s = dict(DEFAULTS)
    for k, v in settings.items():
        if k not in DEFAULTS:
            raise SettingsError(f"unknown setting {k!r}")
        s[k] = _coerce(k, v)
    for k, allowed in CHOICES.items():
        if s[k] not in allowed:
            raise SettingsError(f"{k} must be one of {', '.join(allowed)}, got {s[k]!r}")
    for k in INT_KEYS:
        if isinstance(s[k], bool) or not isinstance(s[k], int):
            raise SettingsError(f"{k} must be an integer, got {s[k]!r}")
    if s["top_k"] < 1:
        raise SettingsError("top_k must be at least 1")
    if s["chunk_size"] < 1:
        raise SettingsError("chunk_size must be at least 1")
    if not 0 <= s["overlap"] < s["chunk_size"]:
        raise SettingsError(f"overlap must satisfy 0 <= overlap < chunk_size, got overlap={s['overlap']} chunk_size={s['chunk_size']}")
    if s["neighbours_n"] < 0:
        raise SettingsError("neighbours_n must not be negative")
    if s["context_token_limit"] < 1:
        raise SettingsError("context_token_limit must be at least 1")
    if not isinstance(s["temperature"], (int, float)) or isinstance(s["temperature"], bool) or not 0 <= s["temperature"] <= 2:
        raise SettingsError("temperature must be a number from 0 to 2")
    bad = [d for d in s["defences"] if d not in DEFENCES]
    if bad:
        raise SettingsError(f"unknown defence {bad[0]!r}; known: {', '.join(DEFENCES)}")
    s["defences"] = sorted(set(s["defences"]), key=DEFENCES.index)
    if s["model_path"] == "hosted" and not s["hosted_model"]:
        raise SettingsError("model_path=hosted needs hosted_model")
    return s


def _flatten(table: dict, out: dict) -> dict:
    for k, v in table.items():
        if isinstance(v, dict):
            _flatten(v, out)
        elif k in DEFAULTS:
            out[k] = v
    return out


def read_toml(path: Path | None = None) -> dict:
    path = path or ROOT / "config" / "settings.toml"
    if not path.exists():
        return {}
    return _flatten(tomllib.loads(path.read_text(encoding="utf-8")), {})


def load_settings(overrides: dict | None = None, base: dict | None = None, path: Path | None = None) -> dict:
    """defaults < config/settings.toml (or `path`) < base (a parent run's resolved settings) < overrides."""
    merged = dict(read_toml(path))
    merged.update(base or {})
    merged.update(overrides or {})
    return validate(merged)


def resolved(settings: dict | None) -> dict:
    """What the Agent uses: a complete dict is validated as given; the toml file is not read."""
    return validate(settings or {})
