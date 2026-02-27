---
name: fix-status-checks
description: Fix failing status checks on the current branch's PR. Use when the user has a PR (e.g. from yeet) and status checks are failing—inspect, fix, and push.
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh auth status`. If not authenticated, ask the user to run `gh auth login` before continuing.

## Workflow

- Inspect failing checks: `gh pr checks` (or `gh pr view` to confirm PR).
- For GitHub Actions failures, fetch logs: `gh run view <run_id> --log` (run_id from the check's details URL).
- Fix the issue (often missing deps, lint errors, or simple code fixes). If checks failed due to deps/tools, install dependencies and rerun locally.
- Stage and commit tersely: `git add -A` then `git commit -m "{fix description}"`
- Push: `git push`
- Recheck: `gh pr checks` to confirm.
