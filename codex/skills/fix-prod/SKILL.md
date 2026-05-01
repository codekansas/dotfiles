---
name: "fix-prod"
description: "Fix broken default-branch checks or production health, adding pre-merge integration tests."
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install `gh` and stop.
- Require authenticated `gh` session. Run `gh auth status`. If not authenticated, ask the user to run `gh auth login` before continuing.
- If production investigation depends on a provider CLI such as `vercel`, `netlify`, `wrangler`, `render`, `flyctl`, `kubectl`, `sentry-cli`, or a repo-specific CLI, prefer the repo's documented command path. If the required CLI is missing or unauthenticated and GitHub cannot provide equivalent signals, report the blocker and stop before making risky assumptions.

## Naming Conventions

- Fix branch: `codex/fix-prod-{description}`.
- Commit message: `fix prod: {description}`.
- PR title: `[codex] fix prod: {description}`.

## Workflow

1. Discover repository, default branch, and production contract:
   - `git status -sb`
   - `git branch --show-current`
   - `git remote -v`
   - Preferred default branch lookup: `gh repo view --json nameWithOwner,defaultBranchRef,url --jq '.defaultBranchRef.name'`
   - Fallback default branch lookup: `git remote show origin` and parse `HEAD branch`.
   - Search local config first: `.github/workflows`, `.circleci`, `.buildkite`, `render.yaml`, `vercel.json`, `netlify.toml`, `Dockerfile*`, `docker-compose*`, `Makefile`, `Taskfile*`, `package.json`, `pyproject.toml`, `README*`, `docs/**`, `scripts/**`, `bin/**`, and existing integration tests.
   - Search for release and health terms: `rg -n "prod|production|deploy|deployment|environment|health|smoke|integration|e2e|synthetic|sentry|error|rollout|promote|workflow_dispatch" ...`
   - Determine the production environment, production deploy trigger, production status source, concrete health checks, error/incident signals, and how to identify the deployed SHA/ref.
   - If local inspection is insufficient, inspect remote metadata:
     - `gh api repos/{owner}/{repo}/branches --paginate --jq '.[].name'`
     - `gh api repos/{owner}/{repo}/actions/workflows`
     - `gh run list --limit 50 --json databaseId,workflowName,headBranch,headSha,event,status,conclusion,url,createdAt`
     - `gh api repos/{owner}/{repo}/environments`
     - `gh api repos/{owner}/{repo}/deployments?per_page=50`
2. Check whether the default branch is healthy:
   - Fetch the default branch:
     - `git fetch origin "{default_branch}"`
   - Resolve the current default-branch SHA:
     - `default_sha=$(git rev-parse "origin/{default_branch}")`
   - Inspect GitHub Actions runs and commit checks for that SHA:
     - `gh run list --branch "{default_branch}" --commit "$default_sha" --json databaseId,workflowName,status,conclusion,url,headSha,createdAt`
     - `gh api repos/{owner}/{repo}/commits/$default_sha/check-runs`
     - `gh api repos/{owner}/{repo}/commits/$default_sha/status`
   - Inspect branch protection or rulesets when available to identify required pre-merge checks:
     - `gh api repos/{owner}/{repo}/branches/{default_branch}/protection`
     - `gh api repos/{owner}/{repo}/rulesets --paginate`
   - Record any failed, missing, pending-too-long, or flaky required/default-branch checks.
3. Check whether the default branch has propagated to production:
   - Identify the latest production deployment, workflow run, provider status, release object, or production branch ref.
   - Confirm production reports `default_sha` or the documented production ref derived from it.
   - If production is behind, stale, serving a different SHA, or has no reliable SHA signal, record that as a propagation problem.
4. Check whether production is stable:
   - Run the repo's documented production health checks and smoke tests.
   - Check deployment status, rollout status, runtime logs, provider incidents, error tracker signals, alerting dashboards, and synthetic checks when configured.
   - Use concrete thresholds from the repo or monitoring config. If no threshold exists, require an obviously healthy baseline: successful deployment status, passing health endpoint or smoke test, no recent crash loops, and no fresh high-severity errors tied to the deployed SHA.
   - Record the exact production failure: failed health check, bad response, missing migration, runtime exception, error spike, rollback, stale cache/CDN, feature flag mismatch, bad config, or deployment system failure.
5. If everything is healthy, report success without changing code:
   - Default branch SHA checked.
   - Default-branch checks observed.
   - Production SHA/ref observed.
   - Production health, stability, and issue signals checked.
   - Any verification gap caused by missing deployment metadata, health checks, or observability.
6. Create a fix branch before making changes:
   - Do not commit directly to the default branch.
   - If currently on the default branch, create `codex/fix-prod-{description}` from `origin/{default_branch}`.
   - If currently on another branch, switch to a fresh fix branch from `origin/{default_branch}` unless the user explicitly wants to reuse the current branch.
   - Keep unrelated local changes out of the fix. If the checkout is dirty with unrelated work, report the blocker and avoid sweeping it into the production fix.
7. Add integration coverage before or alongside the fix:
   - For every code-side production/default-branch failure, add or extend an integration, smoke, contract, migration, or end-to-end test that would have caught the issue before merge.
   - Wire the test into pre-merge checks: prefer existing `pull_request` CI workflows, test scripts, Make targets, or package commands already used by required checks.
   - The integration test should run against a local, test, preview, mocked, or ephemeral environment. Do not make PR checks depend on live production unless the repository already does so intentionally.
   - Make the test deterministic and focused on the observed failure mode. Avoid broad, slow, or flaky coverage that developers will disable later.
   - When practical, prove the new test fails before the production fix and passes after it. If not practical, explain why and still run the nearest reliable validation.
8. Implement the production/default-branch fix:
   - Inspect failing default-branch logs with `gh run view <run_id> --log`.
   - Inspect deployment events, provider logs, runtime logs, migrations, config, release scripts, feature flags, cache/CDN behavior, and smoke-test output as relevant.
   - Patch the smallest code, config, workflow, script, or test change that addresses the root cause.
   - If production propagation failed because the deploy path is missing or manual-only but clear, add a thin repo-native script or workflow step that makes propagation verifiable and repeatable.
   - Do not hardcode secrets, tokens, provider credentials, or environment-specific values.
9. Validate locally and through pre-merge CI:
   - Run the new or updated integration test locally when possible.
   - Run focused local tests, linters, type checks, and `git diff --check`.
   - Commit and push the fix branch:
     - `git add -A`
     - `git commit -m "fix prod: {description}"`
     - `git push -u origin $(git branch --show-current)`
   - Create or update the PR:
     - `gh pr view --json number,state,headRefName,baseRefName,url`
     - `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --head "$(git branch --show-current)" --base "{default_branch}" --title "[codex] fix prod: {description}" --body-file {body_file}`
   - Wait for the PR's pre-merge checks. If the new integration coverage is not part of CI, fix CI wiring before merging.
10. Merge only after checks pass:
   - Use the repository's normal merge path, respecting required reviews, branch protection, rulesets, and merge queues.
   - Prefer `gh pr merge --squash --delete-branch` unless the repository uses another standard mode.
   - Capture the merged PR number and merge commit SHA.
   - Fetch until the merge commit is reachable from `origin/{default_branch}`.
11. Verify the default branch, production propagation, and production stability again:
   - Re-run the default-branch check inspection for the merge commit.
   - Wait for required default-branch checks to pass.
   - Wait for production to deploy or propagate the merge commit through the documented path.
   - Verify production reports the expected SHA/ref.
   - Re-run production health checks, smoke tests, stability checks, and issue/error queries.
   - If default-branch checks, propagation, or production stability still fail, repeat the fix branch + integration-test + PR loop until all code-side failures are resolved.
12. Finish with a concise report:
   - Original default-branch SHA and final default-branch SHA.
   - Failed checks, propagation gaps, or production issues found.
   - Integration tests added to pre-merge checks.
   - PR number, merge commit SHA, and CI status.
   - Production deployment/status URL, deployed SHA/ref, and health/stability checks run.
   - Any remaining non-code blocker such as missing credentials, manual approval, provider outage, or absent observability.

## Guardrails

- Do not commit directly to `main`, `master`, or the repository default branch.
- Do not bypass branch protections, required reviews, merge queues, deployment approvals, or environment gates.
- Do not claim production is fixed until the default branch is green, the expected SHA/ref is live in production, and production health/stability checks pass.
- Do not rely only on GitHub check success when production is unhealthy or stale.
- Do not add superficial tests just to satisfy the requirement; tie new integration coverage to the observed production/default-branch failure mode.
- Do not make PR checks flaky by depending on live production unless the repository already has an intentional production smoke-test gate.
- If production status, deployed SHA, health checks, or issue signals cannot be discovered, report the verification gap clearly and stop before making risky production changes.
