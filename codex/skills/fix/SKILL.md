---
name: "fix"
description: "Use when the user asks to resolve remote GitHub PR push blockers, including failing status checks, merge conflicts, stale base branches, or related CI/merge errors. Handle both feature branches and default branches: if currently on main/master/default, create a fix branch and PR, then iterate commits until the PR checks pass and the original blocker is resolved."
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install `gh` and stop.
- Require authenticated `gh` session. Run `gh auth status`. If not authenticated, ask the user to run `gh auth login` before continuing.

## Naming Conventions

- Fix branch when starting on default branch: `codex/fix-{description}`.
- Commit message: `{fix description}` (terse and specific).
- PR title (when creating one): `[codex] fix: {description}`.

## Workflow

1. Identify repository default branch:
   - Preferred: `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`
   - Fallback: parse `git remote show origin` (`HEAD branch`).
2. Capture current state and the original blocking condition:
   - `git status -sb`
   - `git branch --show-current`
   - `gh pr view --json number,state,headRefName,baseRefName,mergeStateStatus,url` (if a PR already exists)
   - Record the specific error to eliminate (failed check name, merge conflict, non-fast-forward push rejection, etc.).
3. Choose branch strategy:
   - If on non-default branch: stay on this branch and repair the existing PR (or create one if missing).
   - If on default branch: create a fix branch from default (`git checkout -b "codex/fix-{description}"`) and do all fixes there.
4. Ensure remote branch and PR exist for the fix work:
   - Push branch: `git push -u origin $(git branch --show-current)`
   - Create PR when missing: `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --fill --head $(git branch --show-current)`
5. Triage blockers and apply fixes:
   - Failing checks: `gh pr checks`, then inspect failing GitHub Actions logs via `gh run view <run_id> --log`.
   - Merge conflicts/stale branch: `git fetch origin` then merge default into branch (`git merge origin/<default-branch>`) and resolve conflicts.
   - Push rejection (non-fast-forward): `git fetch origin` then integrate remote changes before retrying push.
   - Other actionable CI blockers: reproduce locally when possible and patch.
6. Commit and push each fix iteration:
   - `git add -A`
   - `git commit -m "{fix description}"` (skip commit if no changes)
   - `git push`
7. Re-evaluate blockers after each push:
   - `gh pr checks`
   - `gh pr view --json mergeStateStatus,mergeable,url`
   - Continue iterating steps 5-7 until both are true:
     - PR required checks are passing.
     - The original blocking condition is resolved (the initial error no longer reproduces/is no longer reported).
8. Final verification:
   - Re-run the command that originally failed (or equivalent check) to confirm the blocker is gone.
   - Report PR URL and what was fixed.

## Guardrails

- Do not commit directly to `main` / `master` / default branch when using this skill; always use a fix branch + PR.
- Do not force-push or rewrite history unless the user explicitly asks.
- Do not claim success just because checks are green; explicitly confirm the original blocking error is resolved.
- If the remaining blocker is non-code (for example required review/approval policy), report it clearly and stop after all code-side blockers are fixed.
