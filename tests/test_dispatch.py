"""Tests for dispatch routing, load_config, and _client."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from conftest import make_get_client, make_post_client
from run import dispatch, load_config, _client


# ---------------------------------------------------------------------------
# dispatch — routes known actions
# ---------------------------------------------------------------------------

ALL_ACTIONS = [
    "register", "status", "home", "post", "comment", "verify",
    "feed", "search", "upvote", "dm_list", "dm_read", "dm_send",
]


@pytest.mark.parametrize("action", ALL_ACTIONS)
def test_dispatch_known_actions_do_not_crash(action):
    """Each known action should be routed without raising an unexpected error.

    We supply enough args to avoid validation exits for actions that require them.
    """
    # Build a client that handles both GET and POST
    # GET response needs "messages" for dm_read compatibility
    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = {"success": True, "data": {
        "id": "x", "api_key": "k", "messages": [],
        "conversations": [], "posts": [],
    }}
    get_resp.raise_for_status = MagicMock()

    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.json.return_value = {"success": True, "data": {"id": "x", "api_key": "k"}}
    post_resp.raise_for_status = MagicMock()

    client = MagicMock()
    client.get.return_value = get_resp
    client.post.return_value = post_resp

    args = {
        "action": action,
        "body": "test body",
        "post_id": "p1",
        "comment_id": "c1",
        "verification_code": "vc1",
        "answer": "1.00",
        "query": "test",
        "conversation_id": "cv1",
        "sort": "hot",
        "limit": 5,
    }
    config = {}

    # upvote exits if both post_id and comment_id are given
    if action == "upvote":
        args.pop("comment_id")

    result = dispatch(action, args, config, client)
    assert isinstance(result, str)


def test_dispatch_unknown_action_exits():
    client = MagicMock()
    with pytest.raises(SystemExit):
        dispatch("nonexistent_action", {}, {}, client)


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_no_file_returns_empty(tmp_path):
    with patch("run.Path") as mock_path_cls:
        # Make Path(__file__) return something whose .parent / "config.toml" doesn't exist
        fake_config = tmp_path / "config.toml"
        mock_path_cls.return_value.parent.__truediv__ = MagicMock(return_value=fake_config)
        result = load_config()
    assert result == {}


def test_load_config_valid_file(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[settings]\ndefault_submolt = "general"\n')

    with patch("run.Path") as mock_path_cls:
        mock_parent = MagicMock()
        mock_parent.__truediv__ = MagicMock(return_value=config_file)
        mock_path_cls.return_value.parent = mock_parent
        result = load_config()

    assert result["settings"]["default_submolt"] == "general"


# ---------------------------------------------------------------------------
# _client
# ---------------------------------------------------------------------------

def test_client_with_api_key():
    client = _client("sk-test-key")
    assert client.headers["Authorization"] == "Bearer sk-test-key"
    assert client.headers["Content-Type"] == "application/json"


def test_client_without_api_key():
    client = _client("")
    assert "Authorization" not in client.headers
    assert client.headers["Content-Type"] == "application/json"
