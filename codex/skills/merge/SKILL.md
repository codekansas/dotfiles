---
name: "merge"
description: "Use when the user explicitly asks to take current local git changes all the way to the repository default branch in one flow: stage/commit uncommitted work, push a branch, create or reuse a PR, fix failing status checks until green, and merge into main/master/default via GitHub CLI."
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install `gh` and stop.
- Require authenticated `gh` session. Run `gh auth status`. If not authenticated, ask the user to run `gh auth login` (and re-run `gh auth status`) before continuing.

## Naming Conventions

- Branch when starting from default branch: `codex/{description}`.
- Commit message: `{description}` (terse and specific).
- PR title: `[codex] {description}` summarizing the full diff.

## Workflow

1. Discover the repository default branch:
   - Preferred: `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`
   - Fallback: `git remote show origin` and parse `HEAD branch`.
2. Inspect working tree and current branch:
   - `git status -sb`
   - `git branch --show-current`
3. Detect stale upstream branch or merged PR state:
   - Upstream deleted/unset: `git rev-parse --abbrev-ref --symbolic-full-name @{u}` fails, or `git ls-remote --exit-code --heads origin $(git branch --show-current)` fails.
   - Current branch PR already merged: `gh pr view --json state,mergedAt --jq '.state'` returns `MERGED`.
4. If either stale condition is true, rebase onto `master` (or the repo default branch) and start a fresh PR branch:
   - `git fetch origin`
   - `git rebase origin/<default-branch>` (this is `origin/master` when default is `master`)
   - `git checkout -b "codex/{description}-rebased"`
   - Do not reuse the merged PR; always create a new PR after pushing this rebased branch.
5. If currently on the default branch and there are local changes, create a feature branch:
   - `git checkout -b "codex/{description}"`
6. Stage and commit all local work if anything is uncommitted:
   - `git add -A`
   - `git commit -m "{description}"`
   - If there are no staged changes, continue without creating a new commit.
7. Push current branch with upstream tracking:
   - `git push -u origin $(git branch --show-current)`
8. Ensure a PR exists for the current branch:
   - Check existing PR: `gh pr view --json number,state,headRefName,baseRefName`
   - If no PR exists, create one:
     - `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --fill --head $(git branch --show-current)`
9. Enter a fix loop until status checks pass:
   - Check status: `gh pr checks`
   - For failed GitHub Actions jobs, inspect logs via run ID from details URL:
     - `gh run view <run_id> --log`
   - Apply fixes locally, then repeat commit/push:
     - `git add -A`
     - `git commit -m "{fix description}"`
     - `git push`
   - Re-run `gh pr checks` and continue until all required checks are green.
10. Merge the PR into the default branch once checks are green:
   - `gh pr merge --squash --delete-branch`
   - If branch protection requires auto-merge/queue, use the appropriate `gh pr merge --auto ...` mode.
11. Sync local default branch after merge:
   - `git checkout <default-branch>`
   - `git pull --ff-only`

## Guardrails

- Do not rewrite history or force-push unless the user explicitly asks.
- Do not merge while required checks are failing.
- If a check is external and logs are unavailable in GitHub CLI, report the provider/details URL and proceed with any locally actionable fixes first.
