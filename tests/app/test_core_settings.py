"""Settings validation and the load order."""
import pytest

from app.settings import DEFAULTS, SettingsError, load_settings, validate


def test_defaults_are_the_baseline():
    s = validate({})
    assert s == DEFAULTS | {"defences": []}
    assert (s["pack"], s["model"], s["embed_model"], s["temperature"], s["top_k"], s["chunker"], s["chunk_size"], s["overlap"], s["retriever"],
            s["context"], s["neighbours_n"], s["context_token_limit"]) == ("quillon", "qwen3:4b-instruct", "nomic-embed-text", 0.2, 5, "fixed", 400, 0,
                                                                          "bm25", "none", 1, 3000)
    assert (s["authority_rule"], s["tools"], s["rules"], s["topology"], s["trace_steps"], s["region"], s["emergency_number"]) == (
        "off", "off", "off", "single", "off", "Port Avery", "112")


@pytest.mark.parametrize("bad", [
    {"overlap": 400}, {"overlap": 500}, {"overlap": -1}, {"chunk_size": 0}, {"chunk_size": 100, "overlap": 100},
    {"top_k": 0}, {"retriever": "magic"}, {"chunker": "sentence"}, {"context": "everything"}, {"tools": "maybe"}, {"rules": 2},
    {"topology": "swarm"}, {"defences": ["access", "firewall"]}, {"temperature": 3}, {"temperature": -0.1}, {"pack": "acme"},
    {"model_path": "cloud"}, {"model_path": "hosted"}, {"context_token_limit": 0}, {"neighbours_n": -1}, {"nonsense": 1}, {"top_k": "many"},
])
def test_invalid_settings_are_rejected(bad):
    with pytest.raises(SettingsError):
        validate(bad)


def test_overlap_one_below_the_size_is_allowed_and_equal_is_not():
    assert validate({"chunk_size": 100, "overlap": 99})["overlap"] == 99
    with pytest.raises(SettingsError, match="overlap"):
        validate({"chunk_size": 100, "overlap": 100})


def test_hosted_path_needs_a_hosted_model():
    assert validate({"model_path": "hosted", "hosted_model": "some-model"})["model_path"] == "hosted"
    assert validate({"model_path": "stub"})["model_path"] == "stub"


def test_strings_from_the_command_line_are_coerced():
    s = validate({"top_k": "7", "temperature": "0.5", "defences": "marking, access", "tools": True, "rules": False})
    assert (s["top_k"], s["temperature"], s["defences"], s["tools"], s["rules"]) == (7, 0.5, ["access", "marking"], "on", "off")


def test_load_order_is_defaults_then_toml_then_base_then_overrides(tmp_path, monkeypatch):
    from app import settings
    toml = tmp_path / "settings.toml"
    toml.write_text('top_k = 4\nretriever = "trigram"\n[lab2]\nchunk_size = 300\n[clinic]\nregion = "Elsewhere"\nemergency_number = "999"\nignored_key = 1\n')
    monkeypatch.setattr(settings, "read_toml", lambda path=None: settings._flatten(__import__("tomllib").loads(toml.read_text()), {}))
    s = load_settings()
    assert (s["top_k"], s["retriever"], s["chunk_size"], s["region"], s["emergency_number"]) == (4, "trigram", 300, "Elsewhere", "999")
    s = load_settings(base={"top_k": 6, "retriever": "bm25"})
    assert (s["top_k"], s["retriever"]) == (6, "bm25")
    s = load_settings(overrides={"top_k": 9}, base={"top_k": 6})
    assert s["top_k"] == 9
    with pytest.raises(SettingsError):
        load_settings(overrides={"overlap": 300})                                    # the toml's chunk_size 300 is in force
    with pytest.raises(SettingsError):
        load_settings(overrides={"unknown": 1})


def test_the_agent_validates_the_settings_it_is_given():
    from fixtures_app import make_agent
    with pytest.raises(SettingsError):
        make_agent(overlap=999)
