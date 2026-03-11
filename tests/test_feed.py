"""Tests for feed, search, upvote actions."""
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from run import do_feed, do_search, do_upvote, _format_posts


# ---------------------------------------------------------------------------
# _format_posts
# ---------------------------------------------------------------------------

SAMPLE_POSTS = [
    {"id": "p1", "title": "Hello world", "author": {"name": "agent-a"}, "score": 5, "submolt": "general"},
    {"id": "p2", "body": "No title post here", "author": "agent-b", "score": 0},
]


def test_format_posts_includes_ids():
    result = _format_posts(SAMPLE_POSTS)
    assert "[p1]" in result
    assert "[p2]" in result


def test_format_posts_author_dict():
    result = _format_posts(SAMPLE_POSTS)
    assert "agent-a" in result


def test_format_posts_author_string():
    result = _format_posts(SAMPLE_POSTS)
    assert "agent-b" in result


def test_format_posts_submolt():
    result = _format_posts(SAMPLE_POSTS)
    assert "general" in result


def test_format_posts_empty():
    assert _format_posts([]) == "No posts."


def test_format_posts_uses_body_when_no_title():
    posts = [{"id": "px", "body": "Just a body text here", "author": "x"}]
    result = _format_posts(posts)
    assert "Just a body text" in result


# ---------------------------------------------------------------------------
# do_feed
# ---------------------------------------------------------------------------

def _mock_get_client(json_body: dict):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.get.return_value = resp
    return client


def test_do_feed_returns_formatted_posts():
    client = _mock_get_client({"data": {"posts": SAMPLE_POSTS}})
    result = do_feed(client, "hot", 10, None)
    assert "[p1]" in result


def test_do_feed_passes_sort_and_limit():
    client = _mock_get_client({"data": {"posts": []}})
    do_feed(client, "new", 5, "tech")
    call_params = client.get.call_args[1].get("params", {})
    assert call_params.get("sort") == "new"
    assert call_params.get("limit") == 5
    assert call_params.get("submolt") == "tech"


def test_do_feed_defaults_sort_hot():
    client = _mock_get_client({"data": {"posts": []}})
    do_feed(client, None, 10, None)
    call_params = client.get.call_args[1].get("params", {})
    assert call_params.get("sort") == "hot"


def test_do_feed_flat_list_response():
    client = _mock_get_client(SAMPLE_POSTS)
    result = do_feed(client, "hot", 10, None)
    # Should not crash even if API returns a list directly
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# do_search
# ---------------------------------------------------------------------------

def test_do_search_posts_and_comments():
    client = _mock_get_client({
        "data": {
            "posts": SAMPLE_POSTS,
            "comments": [{"post_id": "p1", "body": "A comment here"}],
        }
    })
    result = do_search(client, "hello", 10)
    assert "Posts" in result
    assert "Comments" in result
    assert "A comment here" in result


def test_do_search_no_results():
    client = _mock_get_client({"data": {"posts": [], "comments": []}})
    result = do_search(client, "nothing", 10)
    assert "No results" in result


def test_do_search_missing_query_exits():
    with pytest.raises(SystemExit):
        do_search(MagicMock(), "", 10)


# ---------------------------------------------------------------------------
# do_upvote
# ---------------------------------------------------------------------------

def _mock_post_client():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"success": True}
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.post.return_value = resp
    return client


def test_do_upvote_post():
    client = _mock_post_client()
    result = do_upvote(client, "p1", None)
    assert "p1" in result
    client.post.assert_called_once()
    assert "/posts/p1/upvote" in client.post.call_args[0][0]


def test_do_upvote_comment():
    client = _mock_post_client()
    result = do_upvote(client, None, "c1")
    assert "c1" in result
    assert "/comments/c1/upvote" in client.post.call_args[0][0]


def test_do_upvote_both_exits():
    with pytest.raises(SystemExit):
        do_upvote(MagicMock(), "p1", "c1")


def test_do_upvote_neither_exits():
    with pytest.raises(SystemExit):
        do_upvote(MagicMock(), None, None)
