# tool-moltbook — Dev Plan

## Overview

Moltbook social network tool for kiso. Enables agents to interact with the Moltbook platform: post content, comment, verify challenges, browse feeds, search, upvote, manage DMs, and handle account registration/status.

## Architecture

- **`run.py`** — single-file plugin (415 lines), all logic in one module
- **HTTP layer** — `httpx.Client` with Bearer auth, base URL `https://www.moltbook.com/api/v1`
- **Config** — optional `config.toml` (e.g. `default_submolt`)
- **Entry point** — `main()` reads JSON from stdin, dispatches to action handler, prints result to stdout

## Capabilities

| Action       | Description                          | Status |
|--------------|--------------------------------------|--------|
| register     | Create agent account                 | done   |
| status       | Show account info (karma, counts)    | done   |
| home         | Dashboard (activity, DMs, feed)      | done   |
| post         | Publish a text post                  | done   |
| comment      | Comment on a post                    | done   |
| verify       | Solve verification challenge         | done   |
| feed         | Browse posts (sort, limit, submolt)  | done   |
| search       | Search posts and comments            | done   |
| upvote       | Upvote a post or comment             | done   |
| dm_list      | List DM conversations                | done   |
| dm_read      | Read messages in a conversation      | done   |
| dm_send      | Send a DM                            | done   |

## Milestones

### M1 — Core actions (post, comment, verify, feed, search, upvote)

- [x] `do_post` with submolt support and verification handling
- [x] `do_comment` with verification handling
- [x] `do_verify` with success/failure paths
- [x] `do_feed` with sort, limit, submolt params
- [x] `do_search` with posts + comments results
- [x] `do_upvote` for posts and comments
- [x] `_format_posts` and `_format_verification` helpers

### M2 — Account & home (register, status, home)

- [x] `do_register` with api_key and claim_url output
- [x] `do_status` with account fields
- [x] `do_home` dashboard with all sections

### M3 — DM actions (dm_list, dm_read, dm_send)

- [x] `do_dm_list` with conversation listing
- [x] `do_dm_read` with message display
- [x] `do_dm_send` with validation

### M4 — Test suite

- [x] `tests/test_post.py` — post, comment, verify actions
- [x] `tests/test_feed.py` — feed, search, upvote actions
- [x] `tests/test_dm.py` — DM actions, status, home

### M5 — Complete test coverage

- [x] `tests/conftest.py` — shared mock helpers
- [x] `tests/test_register.py` — register action tests
- [x] `tests/test_dispatch.py` — dispatch routing, load_config, _client
- [x] `tests/test_main.py` — main() entry point contract
- [x] `tests/test_dm.py` — dm_send API path verification
- [x] `tests/test_feed.py` — search edge cases (posts-only, comments-only)

### M6 — Functional tests (subprocess contract)

**Problem:** `test_main.py` tests only 3 error paths via subprocess (missing
API key, missing action, register without key). No test exercises a successful
action flow end-to-end through `main()` as a real subprocess. The HTTP layer
(`httpx`) is never tested in context of the full stdin→stdout pipe.

**Files:** `tests/test_functional.py` (new)

**Change:**

Tests run `run.py` as a real subprocess. Mock the Moltbook API with
`unittest.mock.patch` inside a wrapper script, or use `respx` / monkeypatch
at the httpx transport level.

1. **Happy path — feed action:**
   - stdin: `{args: {action: "feed"}, ...}` with `KISO_SKILL_MOLTBOOK_API_KEY` set
   - Mock HTTP returns `{data: {posts: [{id: "p1", title: "Test", author: {name: "bot"}, score: 1}]}}`
   - Assert: stdout contains `[p1]`, exit code 0

2. **Happy path — status action:**
   - Mock HTTP returns `{data: {name: "my-agent", karma: 42}}`
   - Assert: stdout contains `my-agent`, exit code 0

3. **Happy path — dm_send action:**
   - Mock HTTP returns `{success: true}`
   - Assert: stdout contains `sent`, exit code 0

4. **Error — HTTP 429 (rate limited):**
   - Mock HTTP raises `HTTPStatusError` with status 429
   - Assert: stderr contains `429`, exit code 1

5. **Error — HTTP timeout:**
   - Mock HTTP raises `TimeoutException`
   - Assert: stderr contains `timed out`, exit code 1

6. **Error — network error:**
   - Mock HTTP raises `RequestError`
   - Assert: stderr contains `network error`, exit code 1

7. **Malformed input — invalid JSON:**
   - Send `"not json"` on stdin
   - Assert: exit code 1

8. **Malformed input — missing args key:**
   - stdin: `{}`
   - Assert: exit code 1

- [x] Implement functional test file with mock HTTP transport
- [x] All 8 functional tests pass
- [x] Total test count verified

---

### M7 — SIGTERM graceful shutdown test

**Problem:** `run.py` registers a SIGTERM handler but no test verifies
the process exits cleanly on SIGTERM.

**Files:** `tests/test_functional.py` (add to existing)

**Change:**

1. Start `run.py` as subprocess with a mock HTTP server that delays response
2. Send `SIGTERM` after 0.5s
3. Assert: process exits 0 (graceful, not crash)

- [x] Implement SIGTERM test
- [x] Passes on Linux

---

## Milestone Checklist

- [x] **M1** — Core actions
- [x] **M2** — Account & home
- [x] **M3** — DM actions
- [x] **M4** — Test suite
- [x] **M5** — Complete test coverage
- [x] **M6** — Functional tests (subprocess contract)
- [x] **M7** — SIGTERM graceful shutdown test
- [ ] **M8** — kiso.toml validation test
- [ ] **M9** — Config error handling

### M8 — kiso.toml validation test

**Problem:** No test verifies that `kiso.toml` is valid and all declared args
are handled in the code.

**Files:** `tests/test_manifest.py` (new)

**Change:**

1. Parse `kiso.toml`, extract arg names from `[kiso.tool.args]`
2. Verify each arg appears in `run.py` (via `args.get("arg_name")`)
3. Verify required TOML sections exist
4. Verify `config.example.toml` is valid TOML (if exists)

- [ ] Implement manifest validation test

---

### M9 — Config error handling: malformed TOML

**Problem:** `load_config()` reads `config.toml` via `tomllib.load()` but
no test verifies behavior when the file contains invalid TOML.

**Files:** `tests/test_config_errors.py` (new)

**Change:**

1. Create a config.toml with invalid content (e.g., `[broken`)
2. Call `load_config()` — should raise `tomllib.TOMLDecodeError` or be handled gracefully
3. Test: missing config.toml → returns `{}` (already tested? verify)

- [ ] Implement config error tests
