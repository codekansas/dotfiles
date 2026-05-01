---
name: "worktree-feature"
description: "Use for $worktree-feature or feature work in a new git worktree: implement, PR, merge, clean up."
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
11. Pull the original checkout after the final successful merge:
   - Check the original checkout before changing it:
     - `git -C "$repo_root" status --short`
     - `git -C "$repo_root" branch --show-current`
   - If the original checkout is clean and not on the base branch, switch it to the base branch:
     - `git -C "$repo_root" switch "{base_branch}"`
   - Pull the original checkout so it contains the new work:
     - `git -C "$repo_root" pull --ff-only`
   - Verify the original checkout now contains the final merge SHA:
     - `git -C "$repo_root" merge-base --is-ancestor "{merge_sha}" HEAD`
   - If the original checkout is dirty or cannot be switched/pulled without overwriting local work, do not force it. Report the exact blocker and leave the checkout untouched.
12. Clean up the feature worktree after the final successful merge:
   - Verify the feature worktree is clean before removing it:
     - `git -C "{worktree_path}" status --short`
   - Remove the sibling worktree from the original checkout:
     - `git -C "$repo_root" worktree remove "{worktree_path}"`
   - Prune stale worktree metadata:
     - `git -C "$repo_root" worktree prune`
   - Confirm the worktree is no longer listed:
     - `git -C "$repo_root" worktree list`
   - Do not force-remove a dirty or blocked worktree. Report the exact blocker and leave the worktree in place for the user to inspect.
13. Finish with a concise report:
   - Worktree path.
   - Whether the worktree was removed successfully.
   - PR number and URL.
   - Merge commit SHA on the base branch.
   - Checks and local validation run.
   - Whether the original checkout was pulled successfully, including the branch and SHA now checked out.
   - `git status --short` for both the worktree and original checkout.

## Guardrails

- Keep the original checkout's uncommitted changes isolated. Do not sweep them into the feature PR unless the user explicitly asks.
- Do not overwrite or remove an existing worktree unless it is clearly the clean worktree for this task.
- Do not force-push or rewrite history unless the user explicitly asks.
- Do not bypass branch protections, required reviews, merge queues, or required status checks.
- Do not report success until the merge commit is reachable from `origin/{base_branch}` and required post-merge checks have passed.
- Do not leave the feature worktree dirty at handoff.
