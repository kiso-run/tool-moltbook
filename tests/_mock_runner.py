"""Helper script that patches httpx before running main().

Usage: python tests/_mock_runner.py <mock_mode>

Mock modes configure what the patched HTTP client returns:
  feed     — returns posts list
  status   — returns account status
  dm_send  — returns success
  http_429 — raises HTTPStatusError 429
  timeout  — raises TimeoutException
  network  — raises RequestError
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

# Add plugin root to sys.path so `import run` works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx


def _make_mock_client(mode: str) -> MagicMock:
    """Build a mock httpx.Client that behaves according to mode."""
    client = MagicMock(spec=httpx.Client)

    if mode == "feed":
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {
                "posts": [
                    {
                        "id": "p1",
                        "title": "Test Post",
                        "author": {"name": "bot"},
                        "score": 1,
                    }
                ]
            }
        }
        resp.raise_for_status = MagicMock()
        client.get.return_value = resp

    elif mode == "status":
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {"name": "my-agent", "karma": 42, "post_count": 5}
        }
        resp.raise_for_status = MagicMock()
        client.get.return_value = resp

    elif mode == "dm_send":
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"success": True}
        resp.raise_for_status = MagicMock()
        client.post.return_value = resp

    elif mode == "http_429":
        error_resp = MagicMock(spec=httpx.Response)
        error_resp.status_code = 429
        error_resp.text = "Rate limited"
        error_resp.json.return_value = {"error": "Rate limited"}
        exc = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=error_resp,
        )
        client.get.side_effect = exc

    elif mode == "timeout":
        client.get.side_effect = httpx.ReadTimeout("read timed out")

    elif mode == "network":
        client.get.side_effect = httpx.ConnectError("connection refused")

    elif mode == "slow":
        # For SIGTERM test: block forever on get
        import time
        import threading

        event = threading.Event()

        def slow_get(*a, **kw):
            event.wait(timeout=30)
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"data": {"posts": []}}
            resp.raise_for_status = MagicMock()
            return resp

        client.get.side_effect = slow_get

    return client


def main():
    mode = sys.argv[1]
    mock_client = _make_mock_client(mode)

    with patch("run._client", return_value=mock_client):
        from run import main as run_main

        run_main()


if __name__ == "__main__":
    main()
