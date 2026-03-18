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
