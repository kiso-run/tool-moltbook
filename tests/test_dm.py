"""Tests for DM actions and home/status."""
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from run import do_dm_list, do_dm_read, do_dm_send, do_home, do_status


def _get_client(json_body: dict):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.get.return_value = resp
    return client


def _post_client(json_body: dict):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.post.return_value = resp
    return client


# ---------------------------------------------------------------------------
# do_status
# ---------------------------------------------------------------------------

def test_do_status_shows_name_and_karma():
    client = _get_client({"data": {"name": "my-agent", "karma": 42, "post_count": 5}})
    result = do_status(client)
    assert "my-agent" in result
    assert "42" in result


def test_do_status_handles_missing_fields():
    client = _get_client({"data": {"name": "x"}})
    result = do_status(client)
    assert "x" in result


# ---------------------------------------------------------------------------
# do_home
# ---------------------------------------------------------------------------

SAMPLE_HOME = {
    "data": {
        "your_account": {"name": "my-agent", "karma": 10, "unread_notifications": 2},
        "latest_moltbook_announcement": {"title": "New feature", "body": "We added something cool today"},
        "activity_on_your_posts": [
            {"post_id": "p1", "body": "Nice reply!"},
        ],
        "your_direct_messages": {"unread_count": 1, "pending_requests": 0},
        "posts_from_accounts_you_follow": [
            {"id": "p2", "title": "Interesting thoughts"},
        ],
    }
}


def test_do_home_shows_account():
    client = _get_client(SAMPLE_HOME)
    result = do_home(client)
    assert "my-agent" in result
    assert "karma: 10" in result


def test_do_home_shows_announcement():
    client = _get_client(SAMPLE_HOME)
    result = do_home(client)
    assert "New feature" in result


def test_do_home_shows_activity():
    client = _get_client(SAMPLE_HOME)
    result = do_home(client)
    assert "p1" in result


def test_do_home_shows_dms():
    client = _get_client(SAMPLE_HOME)
    result = do_home(client)
    assert "1 unread" in result


def test_do_home_shows_feed():
    client = _get_client(SAMPLE_HOME)
    result = do_home(client)
    assert "p2" in result


def test_do_home_empty_response():
    client = _get_client({"data": {}})
    result = do_home(client)
    assert "No activity" in result


# ---------------------------------------------------------------------------
# do_dm_list
# ---------------------------------------------------------------------------

SAMPLE_CONVS = {
    "data": {
        "conversations": [
            {"id": "cv1", "agent": {"name": "other-agent"}, "unread_count": 3, "last_message_at": "2025-01-01"},
        ]
    }
}


def test_do_dm_list_shows_conversations():
    client = _get_client(SAMPLE_CONVS)
    result = do_dm_list(client)
    assert "cv1" in result
    assert "other-agent" in result
    assert "3" in result


def test_do_dm_list_empty():
    client = _get_client({"data": {"conversations": []}})
    result = do_dm_list(client)
    assert "No open" in result


# ---------------------------------------------------------------------------
# do_dm_read
# ---------------------------------------------------------------------------

def test_do_dm_read_shows_messages():
    client = _get_client({
        "data": {
            "messages": [
                {"sender": {"name": "alice"}, "body": "Hello there", "created_at": "2025-01-01T10:00"},
                {"sender": {"name": "me"}, "body": "Hi Alice!", "created_at": "2025-01-01T10:01"},
            ]
        }
    })
    result = do_dm_read(client, "cv1")
    assert "alice" in result
    assert "Hello there" in result
    assert "Hi Alice!" in result


def test_do_dm_read_missing_id_exits():
    with pytest.raises(SystemExit):
        do_dm_read(MagicMock(), "")


def test_do_dm_read_empty():
    client = _get_client({"data": {"messages": []}})
    result = do_dm_read(client, "cv1")
    assert "No messages" in result


# ---------------------------------------------------------------------------
# do_dm_send
# ---------------------------------------------------------------------------

def test_do_dm_send_success():
    client = _post_client({"success": True})
    result = do_dm_send(client, "cv1", "Hey!")
    assert "sent" in result.lower()
    client.post.assert_called_once()


def test_do_dm_send_missing_conv_id_exits():
    with pytest.raises(SystemExit):
        do_dm_send(MagicMock(), "", "body")


def test_do_dm_send_missing_body_exits():
    with pytest.raises(SystemExit):
        do_dm_send(MagicMock(), "cv1", "")


def test_do_dm_send_calls_correct_api_path():
    client = _post_client({"success": True})
    do_dm_send(client, "cv42", "Hello!")
    call_args = client.post.call_args
    path = call_args[0][0]
    assert path == "/agents/dm/conversations/cv42/send"
    payload = call_args[1].get("json") or call_args[0][1]
    assert payload == {"body": "Hello!"}
