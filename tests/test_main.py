"""Tests for main() entry point (subprocess contract)."""
import json
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from run import main


def test_main_missing_api_key_exits(capsys):
    stdin_data = json.dumps({"args": {"action": "status"}})
    with patch("sys.stdin", StringIO(stdin_data)), \
         patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "API key" in captured.err or "API key" in captured.out


def test_main_missing_action_exits(capsys):
    stdin_data = json.dumps({"args": {}})
    with patch("sys.stdin", StringIO(stdin_data)), \
         patch.dict("os.environ", {"KISO_SKILL_MOLTBOOK_API_KEY": "sk-test"}, clear=False):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "action" in captured.err.lower()


def test_main_register_no_api_key_needed(capsys):
    """register action should work even without API key set."""
    stdin_data = json.dumps({"args": {"action": "register"}})
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"api_key": "sk-new"}}
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("sys.stdin", StringIO(stdin_data)), \
         patch.dict("os.environ", {}, clear=True), \
         patch("run._client", return_value=mock_client):
        main()

    captured = capsys.readouterr()
    assert "sk-new" in captured.out
