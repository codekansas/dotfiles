---
name: "worktree-feature"
description: "Use for $worktree-feature or feature work in a new git worktree: implement, pass checks, actually merge/queue, clean up."
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
6. Fix PR checks until they pass:
   - Check status with `gh pr checks`.
   - Wait for required PR checks to reach terminal success before attempting merge or merge-queue entry.
   - If checks are pending, wait and re-check instead of enabling auto-merge as a substitute for passing checks.
   - For failed GitHub Actions jobs, inspect logs via the run ID from the details URL:
     - `gh run view <run_id> --log`
   - For locally actionable failures, implement fixes in the same worktree, commit, push, and re-check.
   - If no checks are configured, state that clearly and proceed based on local validation.
   - Do not merge, enable auto-merge, or enter the merge queue while required checks are failing, pending, or blocked.
   - Passing checks are a prerequisite, not the handoff point. Do not stop after checks pass.
7. Merge or queue the PR:
   - Use squash merge by default:
     - `gh pr merge --squash --delete-branch`
   - If branch protection requires a merge queue, enqueue the PR only after required PR checks are passing. Use the appropriate `gh pr merge --auto ...` or repository-standard queue command, then verify GitHub reports the PR is queued or already merged.
   - Do not treat "merge when ready", a bare auto-merge request, or passing status checks as success. The PR must be either actually merged or explicitly accepted into the merge queue.
   - Do not wait for merge-queue completion, base-branch propagation, post-merge checks, deployment jobs, or production rollout.
   - Capture the PR handoff state:
     - `gh pr view <number> --json state,mergedAt,mergeCommit,mergeStateStatus,autoMergeRequest,url --jq '{state, mergedAt, mergeCommit, mergeStateStatus, autoMergeRequest, url}'`
   - Continue only after `state` is `MERGED`, or after the merge/queue command and PR state show that GitHub accepted the PR into the merge queue. `autoMergeRequest` by itself is not sufficient.
8. Pull the original checkout only when the PR merged immediately:
   - Check the original checkout before changing it:
     - `git -C "$repo_root" status --short`
     - `git -C "$repo_root" branch --show-current`
   - If the PR was queued but not merged yet, do not switch or pull the original checkout. Report that it was left at its current branch and SHA because the merge has not landed yet.
   - If the original checkout is clean and not on the base branch, switch it to the base branch:
     - `git -C "$repo_root" switch "{base_branch}"`
   - Pull the original checkout so it contains the merged work:
     - `git -C "$repo_root" pull --ff-only`
   - When a merge commit SHA is available, verify the original checkout contains it:
     - `git -C "$repo_root" merge-base --is-ancestor "{merge_sha}" HEAD`
   - If the original checkout is dirty or cannot be switched/pulled without overwriting local work, do not force it. Report the exact blocker and leave the checkout untouched.
9. Clean up the feature worktree after the PR is merged or queued:
   - Verify the feature worktree is clean before removing it:
     - `git -C "{worktree_path}" status --short`
   - Remove the sibling worktree from the original checkout:
     - `git -C "$repo_root" worktree remove "{worktree_path}"`
   - Prune stale worktree metadata:
     - `git -C "$repo_root" worktree prune`
   - Confirm the worktree is no longer listed:
     - `git -C "$repo_root" worktree list`
   - Do not force-remove a dirty or blocked worktree. Report the exact blocker and leave the worktree in place for the user to inspect.
10. Finish with a concise report:
   - Worktree path.
   - Whether the worktree was removed successfully.
   - PR number and URL.
   - PR handoff state: merged or queued.
   - Merge commit SHA if the PR merged immediately.
   - Checks and local validation run.
   - Whether the original checkout was pulled successfully or intentionally left unchanged because the PR is still queued.
   - `git status --short` for the original checkout, and the worktree cleanup result.

## Guardrails

- Keep the original checkout's uncommitted changes isolated. Do not sweep them into the feature PR unless the user explicitly asks.
- Do not overwrite or remove an existing worktree unless it is clearly the clean worktree for this task.
- Do not force-push or rewrite history unless the user explicitly asks.
- Do not bypass branch protections, required reviews, merge queues, or required status checks.
- Do not use auto-merge to avoid waiting for required PR checks. Required checks must pass before merge or queue handoff.
- Do not hand off just because checks are passing, tests are running, or "merge when ready" was enabled. Finish by merging the PR or confirming it entered the merge queue.
- Do not wait for production deployment, production health checks, post-merge checks, or merge-queue completion after GitHub has accepted the PR into the queue.
- Do not leave the feature worktree dirty at handoff.
