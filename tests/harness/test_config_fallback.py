"""The harness's own settings check (used before the core exists) refuses what app/settings.py refuses."""
import pytest

from harness import config


@pytest.mark.parametrize("bad", [{"top_k": 0}, {"chunk_size": 0}, {"neighbours_n": -1}, {"context_token_limit": 0},
                                 {"defences": ["firewall"]}, {"model_path": "hosted"}, {"temperature": 3.0}, {"top_k": "5"}])
def test_the_fallback_validator_refuses_what_the_core_refuses(bad):
    with pytest.raises(config.SettingsError):
        config.validate({**config.DEFAULTS, **bad})


def test_the_fallback_validator_accepts_the_defaults_and_known_defences():
    assert config.validate({**config.DEFAULTS, "defences": ["access", "output_check"]})["defences"] == ["access", "output_check"]
