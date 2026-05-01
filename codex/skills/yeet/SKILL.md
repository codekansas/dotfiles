---
name: "yeet"
description: "Use only when asked to commit all local changes, push, and open one PR."
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install `gh` and stop.
- Require authenticated `gh` session. Run `gh auth status`. If not authenticated, ask the user to run `gh auth login` (and re-run `gh auth status`) before continuing.

## Naming conventions

- Branch: `codex/{description}` when starting from main/master/default.
- Commit: `{description}` (terse).
- PR title: `[codex] {description}` summarizing the full branch diff across all commits.

## Workflow

- Discover the repository default branch:
  - Preferred: `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`
  - Fallback: `git remote show origin` and parse `HEAD branch`.
- Check for stale upstream branch or merged PR before pushing:
  - Upstream deleted/unset: `git rev-parse --abbrev-ref --symbolic-full-name @{u}` fails, or `git ls-remote --exit-code --heads origin $(git branch --show-current)` fails.
  - Current branch PR already merged: `gh pr view --json state,mergedAt --jq '.state'` returns `MERGED`.
- If stale condition is true, first rebase onto `master` (or the repo default branch) and start a fresh branch for a new PR:
  - `git fetch origin`
  - `git rebase origin/<default-branch>` (this is `origin/master` when default is `master`)
  - `git checkout -b "codex/{description}-rebased"`
- If still on main/master/default, create a branch: `git checkout -b "codex/{description}"`
- Sweep every dirty file into this one branch and PR:
  - Treat all tracked and untracked files shown by `git status`, whether related to the latest changes or not, as part of this single PR.
  - Do not leave some dirty files behind for a follow-up PR unless the user explicitly asks for that split.
  - If the work falls into multiple topics, create multiple focused commits, but keep them all on this branch and in this PR.
- Confirm status, then stage everything: `git status -sb` then `git add -A`.
- Commit the full dirty tree with one or more focused commits.
- Run checks if not already. If checks fail due to missing deps/tools, install dependencies and rerun once.
- Push with tracking: `git push -u origin $(git branch --show-current)`
- If git push fails due to workflow auth errors, pull from master and retry the push.
- Open a PR and edit title/body to reflect the description and the deltas: `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --draft --fill --head $(git branch --show-current)`
- If the branch came from the stale condition path, always create a new PR and do not reuse the merged PR.
- Write the PR description to a temp file with real newlines (e.g. pr-body.md ... EOF) and run pr-body.md to avoid \\n-escaped markdown.
- PR description (markdown) must be detailed prose covering the issue, the cause and effect on users, the root cause, the fix, and any tests or checks used to validate, and it must summarize the entire branch across all commits.
- Finish by verifying the local work tree is clean with `git status --short`. If anything remains dirty, it still belongs in this same branch/PR flow under this skill.
