---
name: "worktree-feature"
description: "Use for $worktree-feature or feature work in a new git worktree: implement, pass checks, merge every related PR, remove the worktree."
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

## Completion Criteria

- Creating a PR is a checkpoint, not completion.
- Passing checks, enabling auto-merge, or entering a merge queue is not completion.
- The skill is complete only after every PR created or updated for the requested feature is merged, the original checkout has been pulled when safe, and the feature worktree has been removed and pruned.
- If an external blocker such as required human approval prevents merge, do not claim completion. Report the exact blocker, the related PRs, and the retained worktree path.

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
   - Keep an explicit list of every related PR created or updated for this feature. If the implementation or follow-up fixes require multiple PRs, repeat the check, fix, and merge workflow for each PR, then clean up only after all related PRs are merged.
   - Do not stop after the PR is created.
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
7. Merge every related PR:
   - Use squash merge by default:
     - `gh pr merge --squash --delete-branch`
   - If branch protection requires a merge queue, enqueue the PR only after required PR checks are passing. Use the appropriate `gh pr merge --auto ...` or repository-standard queue command, then keep checking until GitHub reports the PR is merged.
   - Do not treat "merge when ready", a bare auto-merge request, queue acceptance, or passing status checks as success. Success requires `state` to be `MERGED` with a non-null `mergedAt`.
   - If a queued PR is dequeued, rejected, or gets new failing checks, inspect the cause, make locally actionable fixes in the same worktree, push them, and repeat the checks and merge step.
   - Do not wait for base-branch propagation, post-merge checks, deployment jobs, or production rollout after every related PR is merged.
   - Capture the final PR state for each related PR:
     - `gh pr view <number> --json state,mergedAt,mergeCommit,mergeStateStatus,autoMergeRequest,url --jq '{state, mergedAt, mergeCommit, mergeStateStatus, autoMergeRequest, url}'`
   - Continue only after every related PR has `state` equal to `MERGED`. `autoMergeRequest` or merge-queue entry by itself is not sufficient.
8. Pull the original checkout after all related PRs are merged:
   - Check the original checkout before changing it:
     - `git -C "$repo_root" status --short`
     - `git -C "$repo_root" branch --show-current`
   - If the original checkout is clean and not on the base branch, switch it to the base branch:
     - `git -C "$repo_root" switch "{base_branch}"`
   - Pull the original checkout so it contains the merged work from every related PR:
     - `git -C "$repo_root" pull --ff-only`
   - When merge commit SHAs are available, verify the original checkout contains each one:
     - `git -C "$repo_root" merge-base --is-ancestor "{merge_sha}" HEAD`
   - If the original checkout is dirty or cannot be switched/pulled without overwriting local work, do not force it. Report the exact blocker and leave the checkout untouched.
9. Clean up the feature worktree after every related PR is merged:
   - Verify the feature worktree is clean before removing it:
     - `git -C "{worktree_path}" status --short`
   - Remove the sibling worktree from the original checkout:
     - `git -C "$repo_root" worktree remove "{worktree_path}"`
   - Prune stale worktree metadata:
     - `git -C "$repo_root" worktree prune`
   - Confirm the worktree is no longer listed:
     - `git -C "$repo_root" worktree list`
   - Do not force-remove a dirty or blocked worktree. Report the exact blocker and leave the worktree in place for the user to inspect.
   - Do not leave a clean feature worktree hanging around after the related PRs are merged.
10. Finish with a concise report:
   - Worktree path.
   - Whether the worktree was removed successfully.
   - PR numbers and URLs for every related PR.
   - Final PR state for every related PR; all should be merged unless an external blocker prevented completion.
   - Merge commit SHAs for merged PRs when available.
   - Checks and local validation run.
   - Whether the original checkout was pulled successfully.
   - `git status --short` for the original checkout, and the worktree cleanup result.

## Guardrails

- Keep the original checkout's uncommitted changes isolated. Do not sweep them into the feature PR unless the user explicitly asks.
- Do not overwrite or remove an existing worktree unless it is clearly the clean worktree for this task.
- Do not force-push or rewrite history unless the user explicitly asks.
- Do not bypass branch protections, required reviews, merge queues, or required status checks.
- Do not use auto-merge to avoid waiting for required PR checks. Required checks must pass before merge or merge-queue entry.
- Do not hand off just because a PR exists, checks are passing, tests are running, "merge when ready" was enabled, or GitHub accepted the PR into a merge queue. Finish by getting every related PR merged.
- Wait for merge-queue completion when a queue is required for the PR to become merged.
- Do not wait for production deployment, production health checks, or post-merge checks after every related PR is merged.
- Do not leave the feature worktree dirty at handoff.
- Do not leave the clean feature worktree present after the related PRs are merged; remove and prune it before finishing.
