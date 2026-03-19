"""Tests for the register action."""
from unittest.mock import MagicMock

from conftest import make_post_client
from run import do_register


def test_do_register_success_with_key_and_claim():
    client = make_post_client({
        "data": {"api_key": "sk-abc123", "claim_url": "https://moltbook.com/claim/xyz"}
    })
    result = do_register(client)
    assert "sk-abc123" in result
    assert "https://moltbook.com/claim/xyz" in result
    assert "Registration successful" in result


def test_do_register_success_without_claim_url():
    client = make_post_client({"data": {"api_key": "sk-def456"}})
    result = do_register(client)
    assert "sk-def456" in result
    assert "claim" not in result.lower()


def test_do_register_output_contains_save_instruction():
    client = make_post_client({"data": {"api_key": "sk-test"}})
    result = do_register(client)
    assert "kiso env set KISO_TOOL_MOLTBOOK_API_KEY" in result
    assert "Save it with" in result
