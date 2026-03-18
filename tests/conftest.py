"""Shared mock helpers for tool-moltbook tests."""
from unittest.mock import MagicMock


def make_get_client(json_body):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.get.return_value = resp
    return client


def make_post_client(json_body):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.post.return_value = resp
    return client
