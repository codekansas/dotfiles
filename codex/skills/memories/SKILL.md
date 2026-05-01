---
name: memories
description: "Maintain repo-local `.memories/` notes for durable multi-step work context."
---

# Repo Memories

Use this skill to keep local-only repo context in `.memories/`.

Treat it as a lightweight local change-tracking and continuity tool for the current repository, not just a user-requested notes feature.

## When To Reach For It

Use it proactively when local repo context would help future work. Do not wait for explicit user prompting.

- Create or update a memory after narrowing down a root cause, debugging path, or implementation plan.
- Capture changed-file context when a task spans multiple files, branches, or partial fixes.
- Record the current state before a risky refactor, interruption, or context switch.
- Summarize what was tried, what failed, and what remains open when a task is not fully done.
- Use it as a local handoff log when the repository has meaningful in-progress state that should survive the current turn.

Prefer short, concrete memories over long narrative logs. A good memory should help another future agent answer: what changed, why it changed, and where to look next.

## Setup

Initialize the current repository once:

```bash
./scripts/memories.sh init
```

This creates `.memories/`, installs `./assets/repo-local/.gitignore` as `.memories/.gitignore`, and adds `/.memories/` to `.git/info/exclude` so the repo does not gain tracked ignore-file changes.

For longer tasks, initialize early and keep the memory fresh as the work evolves.

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

Recommended pattern during longer work:

```bash
./scripts/memories.sh new --title "Current auth refresh investigation" --tags auth,investigation --paths src/auth.ts
./scripts/memories.sh update 20260331-current-auth-refresh-investigation --note "Confirmed failure only happens after token rotation."
./scripts/memories.sh update 20260331-current-auth-refresh-investigation --add-paths tests/auth.test.ts --add-tags flaky
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
- Prefer creating or updating a memory during substantial work rather than relying on ephemeral reasoning alone.
- Keep titles specific enough that a future search query can recover the memory quickly.
- Include file paths, tags, and short notes about what changed so the memory can act like a local change log.
- Put repo-relative file paths in `paths` when a memory is tied to concrete code.
- Run `./scripts/memories.sh organize` after bulk edits or file moves so the lookup indexes stay fresh.
