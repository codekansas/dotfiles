---
name: "worktree-feature"
description: "Use when the user explicitly invokes $worktree-feature or asks to implement a feature in a new git worktree: create a sibling repo-task worktree, implement the requested feature there, open a PR, fix checks until green, merge to master/default, then verify the merge has reached the base branch and post-merge status checks pass."
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install `gh` and stop.
- Require authenticated `gh` session. Run `gh auth status`. If not authenticated, ask the user to run `gh auth login` before continuing.
- Require git worktree support. Run `git worktree list`. If it fails, report the git problem and stop.

## Naming Conventions

- Task slug: derive from the user's requested feature in lowercase kebab-case, keep it short and specific.
- Worktree path: sibling of the current repo root named `{repo-name}-{task-slug}`.
- Branch: `codex/{task-slug}`.
- Commit message: `{task-slug}` or a terse human-readable variant.
- PR title: `[codex] {feature summary}`.
- Fix branches after a merged but broken base branch: `codex/{task-slug}-fix-{n}`.

## Workflow

1. Discover repository context from the original checkout:
   - `repo_root=$(git rev-parse --show-toplevel)`
   - `repo_name=$(basename "$repo_root")`
   - `git status -sb`
   - `git branch --show-current`
   - `git remote -v`
   - Preferred default branch lookup: `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`
   - Fallback default branch lookup: `git remote show origin` and parse `HEAD branch`.
   - Use the repository default branch as the base branch. In repositories where the default branch is `master`, this satisfies the expected master flow. If the user explicitly demanded `master` but the default branch differs, verify `origin/master` exists and stop for clarification if targeting it would conflict with repository policy.
2. Prepare the worktree:
   - Build the worktree path as a sibling directory: `../{repo-name}-{task-slug}` relative to `repo_root`.
   - Run `git fetch origin`.
   - Check `git worktree list --porcelain` before creating anything.
   - If the intended worktree path already exists, reuse it only when it is already a clean worktree for this task. Otherwise pick a unique suffix such as `{repo-name}-{task-slug}-2` and report that adjustment.
   - If the intended branch exists locally or remotely, pick a unique branch suffix such as `codex/{task-slug}-2`.
   - Create the worktree from the latest base branch:
     - `git worktree add -b "{branch}" "{worktree_path}" "origin/{base_branch}"`
   - From this point on, make all implementation edits inside `worktree_path`. Do not modify files in the original checkout except for safe git metadata operations such as fetch.
3. Implement the requested feature in the worktree:
   - Read applicable `AGENTS.md` files inside the worktree before editing.
   - Inspect the codebase and follow existing project patterns.
   - Keep changes focused on the requested feature.
   - Run focused local validation based on the repository and files changed. Prefer documented commands from `README*`, `package.json`, `pyproject.toml`, `Makefile`, `Taskfile*`, or CI workflow files.
   - At minimum, run `git diff --check` before committing.
4. Commit and push from the worktree:
   - `git status -sb`
   - `git add -A`
   - Commit all work for the requested feature. Use multiple commits only when it materially improves review clarity.
   - `git push -u origin $(git branch --show-current)`
5. Create or update the PR:
   - Check for an existing PR: `gh pr view --json number,state,headRefName,baseRefName,url`.
   - If missing, create one:
     - `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --head "$(git branch --show-current)" --base "{base_branch}" --title "[codex] {feature summary}" --body-file {body_file}`
   - The PR body must summarize the feature, important implementation details, validation run, and the worktree path.
6. Fix PR checks until mergeable:
   - Check status with `gh pr checks`.
   - For failed GitHub Actions jobs, inspect logs via the run ID from the details URL:
     - `gh run view <run_id> --log`
   - For locally actionable failures, implement fixes in the same worktree, commit, push, and re-check.
   - Do not merge while required checks are failing, pending, or blocked unless branch protection explicitly queues auto-merge.
7. Merge the PR:
   - Use squash merge by default:
     - `gh pr merge --squash --delete-branch`
   - If branch protection requires auto-merge or a merge queue, use the appropriate `gh pr merge --auto ...` mode and wait for completion.
   - Capture the merged PR number and merge commit SHA:
     - `gh pr view <number> --json state,mergedAt,mergeCommit --jq '{state, mergedAt, mergeCommit}'`
8. Verify propagation to the base branch:
   - Repeatedly fetch the base branch until the merge commit is present:
     - `git fetch origin "{base_branch}"`
     - `git merge-base --is-ancestor "{merge_sha}" "origin/{base_branch}"`
   - If propagation does not happen in a reasonable time, inspect the PR state, merge queue, branch protection, and remote branch refs before reporting a blocker.
   - If the original checkout is already on the base branch and clean, fast-forward it with `git -C "$repo_root" pull --ff-only`. If it is on another branch or dirty, leave it untouched and report that `origin/{base_branch}` is verified.
9. Verify post-merge status checks on the base branch:
   - Inspect GitHub Actions and commit checks for the merge SHA:
     - `gh run list --branch "{base_branch}" --commit "{merge_sha}" --json databaseId,workflowName,status,conclusion,url,headSha,createdAt`
     - `gh api repos/{owner}/{repo}/commits/{merge_sha}/check-runs`
     - `gh api repos/{owner}/{repo}/commits/{merge_sha}/status`
   - Wait for expected checks to reach terminal success.
   - If no checks are configured for the base branch, state that clearly and rely on the local validation already run.
10. Loop on failures after merge:
   - If the base branch checks fail, the feature is missing from the base branch, or the base branch is otherwise unhealthy, debug before reporting success.
   - Inspect failing workflow logs, commit statuses, and relevant local reproduction commands.
   - Reuse the worktree if it is clean, create a fresh fix branch from `origin/{base_branch}`, implement the fix, and repeat the PR/check/merge/propagation verification loop:
     - `git -C "{worktree_path}" switch -c "codex/{task-slug}-fix-{n}" "origin/{base_branch}"`
   - Continue until the intended feature is present on the base branch and post-merge checks pass.
11. Finish with a concise report:
   - Worktree path.
   - PR number and URL.
   - Merge commit SHA on the base branch.
   - Checks and local validation run.
   - Whether the original checkout was fast-forwarded or left untouched.
   - `git status --short` for both the worktree and original checkout.

## Guardrails

- Keep the original checkout's uncommitted changes isolated. Do not sweep them into the feature PR unless the user explicitly asks.
- Do not overwrite or remove an existing worktree unless it is clearly the clean worktree for this task.
- Do not force-push or rewrite history unless the user explicitly asks.
- Do not bypass branch protections, required reviews, merge queues, or required status checks.
- Do not report success until the merge commit is reachable from `origin/{base_branch}` and required post-merge checks have passed.
- Do not leave the feature worktree dirty at handoff.
