---
name: memories
description: Manage repo-local development memories stored in a repository's `.memories/` directory. Use when the user wants to save, list, update, organize, or retrieve local working context, investigation notes, or handoff state without changing tracked repository files.
---

# Repo Memories

Use this skill to keep local-only repo context in `.memories/`.

## Setup

Initialize the current repository once:

```bash
./scripts/memories.sh init
```

This creates `.memories/`, installs `./assets/repo-local/.gitignore` as `.memories/.gitignore`, and adds `/.memories/` to `.git/info/exclude` so the repo does not gain tracked ignore-file changes.

## Commands

Create a new memory:

```bash
./scripts/memories.sh new --title "Root cause for flaky auth refresh" --tags auth,flaky --paths src/auth.ts,tests/auth.test.ts --status active
```

List memories, optionally filtered:

```bash
./scripts/memories.sh list
./scripts/memories.sh list --status active
./scripts/memories.sh list --tag auth
./scripts/memories.sh list --path src/auth.ts --query refresh
```

Update an existing memory:

```bash
./scripts/memories.sh update 20260331-root-cause-for-flaky-auth-refresh --note "Reproduces only with expired refresh tokens."
./scripts/memories.sh update 20260331-root-cause-for-flaky-auth-refresh --status archive --add-tags fixed
```

Rebuild indexes and move entries into the right folders:

```bash
./scripts/memories.sh organize
```

## Layout

The skill keeps:

- `.memories/entries/inbox`, `.memories/entries/active`, `.memories/entries/archive`
- `.memories/index/recent.tsv`
- `.memories/index/by-tag/*`
- `.memories/index/by-path/*`

Each memory is a Markdown file with lightweight front matter for `id`, `title`, `status`, `tags`, `paths`, and timestamps.

## Guardrails

- Prefer `active` for current work, `inbox` for rough captures, and `archive` for settled context.
- Keep titles specific enough that a future search query can recover the memory quickly.
- Put repo-relative file paths in `paths` when a memory is tied to concrete code.
- Run `./scripts/memories.sh organize` after bulk edits or file moves so the lookup indexes stay fresh.
