import json
import os
import signal
import sys
import tomllib
from pathlib import Path

import httpx

BASE_URL = "https://www.moltbook.com/api/v1"
TIMEOUT = 20.0


def _handle_sigterm(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    config_path = Path(__file__).parent / "config.toml"
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _client(api_key: str) -> httpx.Client:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return httpx.Client(base_url=BASE_URL, headers=headers, timeout=TIMEOUT)


def _get(client: httpx.Client, path: str, **params) -> dict:
    resp = client.get(path, params={k: v for k, v in params.items() if v is not None})
    resp.raise_for_status()
    return resp.json()


def _post(client: httpx.Client, path: str, body: dict | None = None) -> dict:
    resp = client.post(path, json=body or {})
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def do_register(client: httpx.Client) -> str:
    data = _post(client, "/agents/register")
    d = data.get("data", data)
    api_key = d.get("api_key", "")
    claim_url = d.get("claim_url", "")
    lines = ["Registration successful.", ""]
    if api_key:
        lines.append(f"API key: {api_key}")
        lines.append("")
        lines.append("Save it with:")
        lines.append(f"  kiso env set KISO_TOOL_MOLTBOOK_API_KEY {api_key}")
    if claim_url:
        lines.append("")
        lines.append(f"Claim URL (visit to link a human owner): {claim_url}")
    return "\n".join(lines)


def do_status(client: httpx.Client) -> str:
    data = _get(client, "/agents/status")
    d = data.get("data", data)
    lines = ["Account status:"]
    for key in ("name", "karma", "post_count", "comment_count", "follower_count", "following_count"):
        if key in d:
            lines.append(f"  {key}: {d[key]}")
    if "restrictions" in d:
        lines.append(f"  restrictions: {d['restrictions']}")
    return "\n".join(lines)


def do_home(client: httpx.Client) -> str:
    data = _get(client, "/home")
    d = data.get("data", data)
    lines = []

    account = d.get("your_account", {})
    if account:
        lines.append(f"Account: {account.get('name', '?')}  karma: {account.get('karma', '?')}  unread notifications: {account.get('unread_notifications', 0)}")
        lines.append("")

    announcement = d.get("latest_moltbook_announcement")
    if announcement:
        lines.append(f"[Announcement] {announcement.get('title', '')} — {announcement.get('body', '')[:120]}")
        lines.append("")

    activity = d.get("activity_on_your_posts", [])
    if activity:
        lines.append(f"Activity on your posts ({len(activity)} item(s)):")
        for item in activity[:5]:
            lines.append(f"  • post {item.get('post_id', '?')}: {item.get('body', '')[:80]}")
        lines.append("")

    dms = d.get("your_direct_messages", {})
    pending = dms.get("pending_requests", 0)
    unread = dms.get("unread_count", 0)
    if pending or unread:
        lines.append(f"DMs: {unread} unread, {pending} pending request(s)")
        lines.append("")

    feed = d.get("posts_from_accounts_you_follow", [])
    if feed:
        lines.append(f"From accounts you follow ({len(feed)} post(s)):")
        for post in feed[:5]:
            lines.append(f"  [{post.get('id', '?')}] {post.get('title', post.get('body', ''))[:80]}")
        lines.append("")

    if not lines:
        lines.append("No activity.")

    return "\n".join(lines).rstrip()


def _format_verification(data: dict) -> str:
    """Return a PENDING_VERIFICATION block from an API response that requires it."""
    d = data.get("data", data)
    code = d.get("verification_code", "")
    challenge = d.get("challenge_text", d.get("challenge", ""))
    lines = [
        "PENDING_VERIFICATION",
        f"code: {code}",
        "",
        "Challenge (solve and call action=\"verify\" with the numeric answer):",
        challenge,
        "",
        "Example: moltbook action=\"verify\" verification_code=\"<code>\" answer=\"3.00\"",
    ]
    return "\n".join(lines)


def do_post(client: httpx.Client, body: str, submolt: str | None, config: dict) -> str:
    if not body:
        print("post requires body", file=sys.stderr)
        sys.exit(1)
    submolt = submolt or config.get("default_submolt") or None
    payload: dict = {"body": body, "type": "text"}
    if submolt:
        payload["submolt"] = submolt
    resp = client.post("/posts", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        if not data.get("success", True):
            return _format_verification(data)
        d = data.get("data", data)
        post_id = d.get("id", "?")
        return f"Post published. ID: {post_id}"
    if resp.status_code == 202:
        # Accepted but needs verification
        return _format_verification(resp.json())
    resp.raise_for_status()
    return "Post published."


def do_comment(client: httpx.Client, post_id: str, body: str) -> str:
    if not post_id:
        print("comment requires post_id", file=sys.stderr)
        sys.exit(1)
    if not body:
        print("comment requires body", file=sys.stderr)
        sys.exit(1)
    resp = client.post(f"/posts/{post_id}/comments", json={"body": body})
    if resp.status_code in (200, 202):
        data = resp.json()
        if not data.get("success", True) or resp.status_code == 202:
            return _format_verification(data)
        d = data.get("data", data)
        comment_id = d.get("id", "?")
        return f"Comment posted. ID: {comment_id}"
    resp.raise_for_status()
    return "Comment posted."


def do_verify(client: httpx.Client, verification_code: str, answer: str) -> str:
    if not verification_code or not answer:
        print("verify requires verification_code and answer", file=sys.stderr)
        sys.exit(1)
    data = _post(client, "/verify", {"verification_code": verification_code, "answer": answer})
    if data.get("success"):
        return "Verification successful. Content published."
    error = data.get("error", "Verification failed.")
    hint = data.get("hint", "")
    msg = f"Verification failed: {error}"
    if hint:
        msg += f"\nHint: {hint}"
    print(msg, file=sys.stderr)
    sys.exit(1)


def do_feed(client: httpx.Client, sort: str, limit: int, submolt: str | None) -> str:
    params: dict = {"sort": sort or "hot", "limit": limit}
    if submolt:
        params["submolt"] = submolt
    data = _get(client, "/posts", **params)
    if isinstance(data, list):
        posts = data
    else:
        posts = data.get("data", data)
        if isinstance(posts, dict):
            posts = posts.get("posts", [])
    return _format_posts(posts)


def do_search(client: httpx.Client, query: str, limit: int) -> str:
    if not query:
        print("search requires query", file=sys.stderr)
        sys.exit(1)
    data = _get(client, "/search", q=query, type="all", limit=limit)
    d = data.get("data", data)
    lines = []
    posts = d.get("posts", [])
    comments = d.get("comments", [])
    if posts:
        lines.append(f"Posts ({len(posts)}):")
        lines.append(_format_posts(posts))
    if comments:
        if lines:
            lines.append("")
        lines.append(f"Comments ({len(comments)}):")
        for c in comments[:limit]:
            lines.append(f"  [{c.get('post_id', '?')}] {c.get('body', '')[:100]}")
    if not lines:
        lines.append(f'No results for "{query}".')
    return "\n".join(lines)


def do_upvote(client: httpx.Client, post_id: str | None, comment_id: str | None) -> str:
    if post_id and comment_id:
        print("upvote: pass post_id or comment_id, not both", file=sys.stderr)
        sys.exit(1)
    if post_id:
        _post(client, f"/posts/{post_id}/upvote")
        return f"Upvoted post {post_id}."
    if comment_id:
        _post(client, f"/comments/{comment_id}/upvote")
        return f"Upvoted comment {comment_id}."
    print("upvote requires post_id or comment_id", file=sys.stderr)
    sys.exit(1)


def do_dm_list(client: httpx.Client) -> str:
    data = _get(client, "/agents/dm/conversations")
    convs = data.get("data", data)
    if isinstance(convs, dict):
        convs = convs.get("conversations", [])
    if not convs:
        return "No open DM conversations."
    lines = [f"DM conversations ({len(convs)}):"]
    for c in convs:
        unread = c.get("unread_count", 0)
        agent = c.get("agent", {}).get("name", "?")
        last = c.get("last_message_at", "")
        conv_id = c.get("id", "?")
        lines.append(f"  [{conv_id}] {agent}  unread: {unread}  last: {last}")
    return "\n".join(lines)


def do_dm_read(client: httpx.Client, conversation_id: str) -> str:
    if not conversation_id:
        print("dm_read requires conversation_id", file=sys.stderr)
        sys.exit(1)
    data = _get(client, f"/agents/dm/conversations/{conversation_id}")
    d = data.get("data", data)
    messages = d.get("messages", d) if isinstance(d, dict) else d
    if not messages:
        return "No messages."
    lines = []
    for m in messages:
        sender = m.get("sender", {}).get("name", "?")
        body = m.get("body", "")
        ts = m.get("created_at", "")
        lines.append(f"[{ts}] {sender}: {body}")
    return "\n".join(lines)


def do_dm_send(client: httpx.Client, conversation_id: str, body: str) -> str:
    if not conversation_id:
        print("dm_send requires conversation_id", file=sys.stderr)
        sys.exit(1)
    if not body:
        print("dm_send requires body", file=sys.stderr)
        sys.exit(1)
    _post(client, f"/agents/dm/conversations/{conversation_id}/send", {"body": body})
    return "Message sent."


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_posts(posts: list) -> str:
    if not posts:
        return "No posts."
    lines = []
    for p in posts:
        post_id = p.get("id", "?")
        title = p.get("title") or p.get("body", "")[:80]
        author = p.get("author", {}).get("name", "?") if isinstance(p.get("author"), dict) else p.get("author", "?")
        score = p.get("score", p.get("upvotes", ""))
        submolt = p.get("submolt", "")
        meta = f"by {author}"
        if submolt:
            meta += f"  in {submolt}"
        if score != "":
            meta += f"  score: {score}"
        lines.append(f"[{post_id}] {title}")
        lines.append(f"  {meta}")
        lines.append("")
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    data = json.load(sys.stdin)
    args = data["args"]

    config = load_config()
    api_key = os.environ.get("KISO_TOOL_MOLTBOOK_API_KEY", "")

    action = args.get("action", "")
    if not action:
        print("Missing required arg: action", file=sys.stderr)
        sys.exit(1)

    if action == "register":
        # No API key needed for registration
        client = _client("")
    else:
        if not api_key:
            print("KISO_TOOL_MOLTBOOK_API_KEY not set. Run action=\"register\" first.", file=sys.stderr)
            print("Error: API key not configured. Run moltbook action=\"register\" to create an account.")
            sys.exit(1)
        client = _client(api_key)

    try:
        result = dispatch(action, args, config, client)
    except httpx.TimeoutException as exc:
        print(f"Moltbook request timed out: {exc}", file=sys.stderr)
        print("Error: request timed out.")
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        body = exc.response.text
        print(f"Moltbook HTTP {exc.response.status_code}: {body}", file=sys.stderr)
        try:
            err = exc.response.json()
            msg = err.get("error", body)
            hint = err.get("hint", "")
            out = f"Error {exc.response.status_code}: {msg}"
            if hint:
                out += f"\nHint: {hint}"
        except Exception:
            out = f"Error {exc.response.status_code}."
        print(out)
        sys.exit(1)
    except httpx.RequestError as exc:
        print(f"Moltbook network error: {exc}", file=sys.stderr)
        print("Error: network error.")
        sys.exit(1)

    print(result)


def dispatch(action: str, args: dict, config: dict, client: httpx.Client) -> str:
    limit = min(args.get("limit", 10), 50)

    if action == "register":
        return do_register(client)
    if action == "status":
        return do_status(client)
    if action == "home":
        return do_home(client)
    if action == "post":
        return do_post(client, args.get("body", ""), args.get("submolt"), config)
    if action == "comment":
        return do_comment(client, args.get("post_id", ""), args.get("body", ""))
    if action == "verify":
        return do_verify(client, args.get("verification_code", ""), args.get("answer", ""))
    if action == "feed":
        return do_feed(client, args.get("sort", "hot"), limit, args.get("submolt"))
    if action == "search":
        return do_search(client, args.get("query", ""), limit)
    if action == "upvote":
        return do_upvote(client, args.get("post_id"), args.get("comment_id"))
    if action == "dm_list":
        return do_dm_list(client)
    if action == "dm_read":
        return do_dm_read(client, args.get("conversation_id", ""))
    if action == "dm_send":
        return do_dm_send(client, args.get("conversation_id", ""), args.get("body", ""))

    print(f"Unknown action: {action!r}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
