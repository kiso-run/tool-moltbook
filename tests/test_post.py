"""Tests for post/comment/verify actions."""
import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from run import do_comment, do_post, do_verify, _format_verification


# ---------------------------------------------------------------------------
# _format_verification
# ---------------------------------------------------------------------------

def test_format_verification_includes_code_and_challenge():
    data = {"data": {"verification_code": "abc123", "challenge_text": "If Alice has 2 apples..."}}
    result = _format_verification(data)
    assert "PENDING_VERIFICATION" in result
    assert "abc123" in result
    assert "Alice has 2 apples" in result
    assert 'action="verify"' in result


def test_format_verification_fallback_challenge_key():
    data = {"data": {"verification_code": "xyz", "challenge": "Solve: 1 + 1"}}
    result = _format_verification(data)
    assert "Solve: 1 + 1" in result


# ---------------------------------------------------------------------------
# do_post
# ---------------------------------------------------------------------------

def _mock_client(status_code: int, json_body: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.post.return_value = resp
    return client


def test_do_post_success():
    client = _mock_client(200, {"success": True, "data": {"id": "p1"}})
    result = do_post(client, "Hello Moltbook!", None, {})
    assert "p1" in result
    assert "published" in result.lower()


def test_do_post_pending_verification_202():
    client = _mock_client(202, {"verification_code": "vc1", "challenge_text": "How many?"})
    result = do_post(client, "Hello!", None, {})
    assert "PENDING_VERIFICATION" in result
    assert "vc1" in result


def test_do_post_pending_verification_200_not_success():
    client = _mock_client(200, {"success": False, "verification_code": "vc2", "challenge_text": "Math?"})
    result = do_post(client, "Hello!", None, {})
    assert "PENDING_VERIFICATION" in result


def test_do_post_uses_default_submolt_from_config():
    client = _mock_client(200, {"success": True, "data": {"id": "p2"}})
    do_post(client, "Test post", None, {"default_submolt": "general"})
    call_args = client.post.call_args
    payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
    assert payload.get("submolt") == "general"


def test_do_post_arg_submolt_overrides_config():
    client = _mock_client(200, {"success": True, "data": {"id": "p3"}})
    do_post(client, "Test", "tech", {"default_submolt": "general"})
    call_args = client.post.call_args
    payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
    assert payload.get("submolt") == "tech"


def test_do_post_missing_body_exits():
    client = MagicMock()
    with pytest.raises(SystemExit):
        do_post(client, "", None, {})


# ---------------------------------------------------------------------------
# do_comment
# ---------------------------------------------------------------------------

def test_do_comment_success():
    client = _mock_client(200, {"success": True, "data": {"id": "c1"}})
    result = do_comment(client, "post123", "Great post!")
    assert "c1" in result


def test_do_comment_missing_post_id_exits():
    with pytest.raises(SystemExit):
        do_comment(MagicMock(), "", "body")


def test_do_comment_missing_body_exits():
    with pytest.raises(SystemExit):
        do_comment(MagicMock(), "p1", "")


def test_do_comment_pending_verification():
    client = _mock_client(202, {"verification_code": "vc3", "challenge_text": "Solve this"})
    result = do_comment(client, "p1", "Nice!")
    assert "PENDING_VERIFICATION" in result


# ---------------------------------------------------------------------------
# do_verify
# ---------------------------------------------------------------------------

def test_do_verify_success():
    client = _mock_client(200, {"success": True})
    result = do_verify(client, "vc1", "3.00")
    assert "successful" in result.lower()


def test_do_verify_failure_exits():
    client = _mock_client(200, {"success": False, "error": "Wrong answer", "hint": "Try again"})
    with pytest.raises(SystemExit):
        do_verify(client, "vc1", "9.99")


def test_do_verify_missing_code_exits():
    with pytest.raises(SystemExit):
        do_verify(MagicMock(), "", "3.00")


def test_do_verify_missing_answer_exits():
    with pytest.raises(SystemExit):
        do_verify(MagicMock(), "vc1", "")
