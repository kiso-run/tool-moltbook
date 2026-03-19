"""Functional tests — run run.py as a real subprocess."""
import json
import os
import signal
import subprocess
import sys
import time

import pytest

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_PY = os.path.join(PLUGIN_DIR, "run.py")
MOCK_RUNNER = os.path.join(PLUGIN_DIR, "tests", "_mock_runner.py")
PYTHON = sys.executable


def _run_main(stdin_data: str, *, env_extra: dict | None = None, use_mock: str | None = None):
    """Run run.py (or mock runner) as subprocess, return (stdout, stderr, returncode)."""
    env = os.environ.copy()
    # Clear API key by default
    env.pop("KISO_TOOL_MOLTBOOK_API_KEY", None)
    if env_extra:
        env.update(env_extra)

    if use_mock:
        cmd = [PYTHON, MOCK_RUNNER, use_mock]
    else:
        cmd = [PYTHON, RUN_PY]

    proc = subprocess.run(
        cmd,
        input=stdin_data,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        cwd=PLUGIN_DIR,
    )
    return proc.stdout, proc.stderr, proc.returncode


# ── Error paths (no HTTP mocking needed) ──


class TestErrorPaths:
    def test_missing_api_key(self):
        stdin = json.dumps({"args": {"action": "status"}})
        stdout, stderr, rc = _run_main(stdin)
        assert rc == 1
        assert "API key" in stderr or "API key" in stdout

    def test_missing_action(self):
        stdin = json.dumps({"args": {}})
        stdout, stderr, rc = _run_main(stdin, env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"})
        assert rc == 1
        assert "action" in stderr.lower()

    def test_invalid_json(self):
        stdout, stderr, rc = _run_main("not json at all")
        assert rc != 0

    def test_missing_args_key(self):
        stdin = json.dumps({})
        stdout, stderr, rc = _run_main(stdin, env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"})
        assert rc != 0

    def test_unknown_action(self):
        stdin = json.dumps({"args": {"action": "bogus_action"}})
        stdout, stderr, rc = _run_main(stdin, env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"})
        assert rc == 1
        assert "Unknown action" in stderr


# ── Happy paths (via mock runner) ──


class TestHappyPaths:
    def test_feed_action(self):
        stdin = json.dumps({"args": {"action": "feed"}})
        stdout, stderr, rc = _run_main(
            stdin,
            env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"},
            use_mock="feed",
        )
        assert rc == 0, f"stderr: {stderr}"
        assert "[p1]" in stdout
        assert "Test Post" in stdout

    def test_status_action(self):
        stdin = json.dumps({"args": {"action": "status"}})
        stdout, stderr, rc = _run_main(
            stdin,
            env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"},
            use_mock="status",
        )
        assert rc == 0, f"stderr: {stderr}"
        assert "my-agent" in stdout
        assert "42" in stdout

    def test_dm_send_action(self):
        stdin = json.dumps({
            "args": {
                "action": "dm_send",
                "conversation_id": "conv-1",
                "body": "hello there",
            }
        })
        stdout, stderr, rc = _run_main(
            stdin,
            env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"},
            use_mock="dm_send",
        )
        assert rc == 0, f"stderr: {stderr}"
        assert "sent" in stdout.lower()


# ── HTTP error paths (via mock runner) ──


class TestHTTPErrors:
    def test_http_429(self):
        stdin = json.dumps({"args": {"action": "feed"}})
        stdout, stderr, rc = _run_main(
            stdin,
            env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"},
            use_mock="http_429",
        )
        assert rc == 1
        assert "429" in stderr or "429" in stdout

    def test_timeout(self):
        stdin = json.dumps({"args": {"action": "feed"}})
        stdout, stderr, rc = _run_main(
            stdin,
            env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"},
            use_mock="timeout",
        )
        assert rc == 1
        assert "timed out" in stderr.lower() or "timed out" in stdout.lower()

    def test_network_error(self):
        stdin = json.dumps({"args": {"action": "feed"}})
        stdout, stderr, rc = _run_main(
            stdin,
            env_extra={"KISO_TOOL_MOLTBOOK_API_KEY": "sk-test"},
            use_mock="network",
        )
        assert rc == 1
        assert "network error" in stderr.lower() or "network error" in stdout.lower()


# ── SIGTERM graceful shutdown (M7) ──


class TestSIGTERM:
    @pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM not available on Windows")
    def test_sigterm_graceful_exit(self):
        """Start run.py with a slow mock, send SIGTERM, verify clean exit 0."""
        stdin_data = json.dumps({"args": {"action": "feed"}})
        env = os.environ.copy()
        env["KISO_TOOL_MOLTBOOK_API_KEY"] = "sk-test"

        proc = subprocess.Popen(
            [PYTHON, MOCK_RUNNER, "slow"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=PLUGIN_DIR,
        )
        # Send stdin and close it so the process can read it
        proc.stdin.write(stdin_data)
        proc.stdin.close()

        # Give the process time to start and enter the slow handler
        time.sleep(0.5)

        # Send SIGTERM
        proc.send_signal(signal.SIGTERM)

        # Wait for exit (stdin already closed, so use wait + read)
        rc = proc.wait(timeout=5)
        stderr = proc.stderr.read()
        assert rc == 0, f"Expected exit 0 but got {rc}. stderr: {stderr}"
