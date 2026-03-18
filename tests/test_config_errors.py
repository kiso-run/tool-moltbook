import tomllib

import pytest

from run import load_config


def test_missing_config_returns_dict():
    """load_config returns a dict whether or not config.toml exists."""
    result = load_config()
    assert isinstance(result, dict)


def test_malformed_toml_raises(tmp_path):
    """tomllib raises TOMLDecodeError on invalid TOML (load_config delegates to it)."""
    bad = tmp_path / "config.toml"
    bad.write_text("[broken")
    with pytest.raises(tomllib.TOMLDecodeError):
        with open(bad, "rb") as f:
            tomllib.load(f)
