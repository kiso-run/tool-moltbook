import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
KISO_TOML = ROOT / "kiso.toml"
RUN_PY = ROOT / "run.py"


def test_kiso_toml_is_valid():
    with open(KISO_TOML, "rb") as f:
        data = tomllib.load(f)
    assert data["kiso"]["type"] == "tool"
    assert data["kiso"]["name"] == "moltbook"
    assert "version" in data["kiso"]
    assert "summary" in data["kiso"]["tool"]


def test_all_declared_args_used_in_code():
    with open(KISO_TOML, "rb") as f:
        data = tomllib.load(f)
    args = data["kiso"]["tool"]["args"]
    source = RUN_PY.read_text()
    for arg_name in args:
        assert arg_name in source, f"Declared arg '{arg_name}' not found in run.py"


def test_required_sections_exist():
    with open(KISO_TOML, "rb") as f:
        data = tomllib.load(f)
    assert "kiso" in data
    assert "tool" in data["kiso"]
    assert "args" in data["kiso"]["tool"]


def test_config_example_toml_valid():
    example = ROOT / "config.example.toml"
    if not example.exists():
        pytest.skip("no config.example.toml")
    with open(example, "rb") as f:
        data = tomllib.load(f)
    assert isinstance(data, dict)


def test_usage_guide_mentions_scope_and_required_args():
    with open(KISO_TOML, "rb") as f:
        data = tomllib.load(f)
    guide = data["kiso"]["tool"]["usage_guide"]
    assert "Do NOT use it for" in guide
    assert "post     — body" in guide
    assert "dm_send  — conversation_id, body" in guide
    assert "`search` is only for Moltbook content" in guide
