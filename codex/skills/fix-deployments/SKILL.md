---
name: "fix-deployments"
description: "Use when the user asks to repair broken GitHub deployments or environments for the current repository. Discover the repository's current deployment environments, order them from lowest-risk to highest-risk (for example Staging before Production), then inspect, patch, redeploy, and verify each environment in sequence until they are healthy."
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install `gh` and stop.
- Require authenticated `gh` session. Run `gh auth status`. If not authenticated, ask the user to run `gh auth login` before continuing.
- If the repo depends on a provider CLI such as `vercel`, `netlify`, `wrangler`, `render`, `flyctl`, or `kubectl`, prefer the repo's documented command path. If the required CLI is missing and GitHub alone cannot complete the fix, ask the user to install or authenticate it and stop.

## Naming Conventions

- Fix branch when starting on the default branch: `codex/fix-deployments-{description}`.
- Commit message: `fix deployment: {environment} {description}`.
- PR title when creating one: `[codex] fix deployment: {environment}`.

## Workflow

1. Discover repository and branch context:
   - `gh repo view --json nameWithOwner,defaultBranchRef,url`
   - `git status -sb`
   - `git branch --show-current`
   - `gh pr view --json number,state,headRefName,baseRefName,mergeStateStatus,url` when a PR already exists
2. Detect stale branch state before fixing anything:
   - Upstream deleted or unset: `git rev-parse --abbrev-ref --symbolic-full-name @{u}` fails, or `git ls-remote --exit-code --heads origin $(git branch --show-current)` fails.
   - Current branch PR already merged: `gh pr view --json state,mergedAt --jq '.state'` returns `MERGED`.
   - If stale, rebase onto the repo default branch and create a fresh fix branch.
   - If on the default branch, create a fix branch before making changes.
3. Discover the current deployment environments and order them safely:
   - Inspect local repo config first: `.github/workflows`, deployment scripts, provider config files, `README*`, `docs/**`, `scripts/**`, `bin/**`.
   - Inspect GitHub deployment metadata:
     - `gh api repos/{owner}/{repo}/environments`
     - `gh api repos/{owner}/{repo}/deployments?per_page=50`
     - `gh run list --limit 50 --json databaseId,workflowName,headBranch,headSha,event,status,conclusion,url,createdAt`
   - Prefer the repo's explicit promotion order if it exists.
   - Otherwise process environments from least-critical to most-critical. Default heuristic:
     - `dev`, `preview`, `review`, `test`, `qa`, `integration`, `staging`, `preprod`, `production`
   - If GitHub or the repo presents environments in the opposite direction, reverse them so lower environments are fixed first.
   - Example: if the current environments are `Production` and `Staging`, process `Staging` before `Production`.
   - If environment order is still ambiguous, stop and ask the user before touching higher environments.
4. For each environment in order, identify the active failure:
   - Find the latest deployment, target ref/SHA, workflow run, and health signal for that environment.
   - Record the specific blocking condition: failed deployment job, bad health check, stale branch, missing script, bad config, or provider-side error.
   - If the environment is already healthy at the intended ref, skip it and continue to the next environment.
5. Triage and patch the current environment before moving on:
   - Inspect deployment logs with `gh run view <run_id> --log` when GitHub Actions is the source of truth.
   - Inspect GitHub deployment statuses or provider-native logs when Actions is not enough.
   - Reproduce locally when possible.
   - If the deployment path is clear but the repo does not yet have a reusable deploy or repair script for this environment, write one in the repo-native location such as `scripts/` or `bin/`, and keep it thin.
   - Patch code, config, scripts, or workflow definitions until the current environment's blocker is addressed.
6. Commit and push each repair iteration:
   - `git add -A`
   - `git commit -m "fix deployment: {environment} {description}"` (skip the commit if there are no staged changes)
   - `git push -u origin $(git branch --show-current)` on first push
   - Ensure a PR exists:
     - `gh pr view --json number,state,headRefName,baseRefName`
     - If no PR exists, create one: `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --fill --head $(git branch --show-current)`
7. Re-evaluate the same environment after each push:
   - `gh pr checks`
   - Re-check the environment's deployment status, workflow run, and health checks.
   - Continue iterating until the current environment is healthy at the intended ref.
8. Only after the current environment is healthy, move to the next one:
   - If the next environment requires merge or promotion, use the repo's existing deployment flow to advance it only after the lower environment is healthy.
   - Repeat steps 4-8 for each remaining environment, ending with the highest-risk environment.
9. Final verification:
   - Confirm every discovered environment is healthy in the final order processed.
   - Report which fixes were applied per environment, which PR or branch carried the changes, and any remaining manual approvals or provider-side blockers.

## Guardrails

- Do not skip a broken lower environment to patch a higher environment first unless the repo explicitly states those environments are independent and the user asks for that exception.
- Do not assume environment names or order; prefer repo-defined promotion flow, then fall back to the default heuristic.
- Do not claim success just because a PR check is green; explicitly confirm each environment's deployment and health.
- Do not bypass branch protections, required approvals, merge queues, or deployment approvals.
- Do not hardcode tokens, API keys, or provider secrets into generated scripts or workflow edits.
- Do not force-push or rewrite history unless the user explicitly asks.
- If the remaining blocker is non-code or outside the repository's control, report it clearly after fixing everything that is locally actionable.
