---
name: "yolo"
description: "Use only when asked to ship all local changes through PR, staging, and production."
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install `gh` and stop.
- Require authenticated `gh` session. Run `gh auth status`. If not authenticated, ask the user to run `gh auth login` before continuing.
- If the repo depends on a provider CLI such as `vercel`, `netlify`, `wrangler`, `render`, `flyctl`, or `kubectl`, prefer the repo's documented command path. If the required CLI is missing and GitHub alone cannot complete the release, ask the user to install or authenticate it and stop.

## Naming Conventions

- Branch when starting from default branch: `codex/{description}`.
- Commit message: `{description}` for the primary change; `{fix description}` for release-loop fixes.
- PR title: `[codex] {description}` summarizing the full branch diff across all commits.
- Promotion branch when one is required: `codex/deploy-prod-{short-sha}`.

## Workflow

1. Discover repository context:
   - `git status -sb`
   - `git branch --show-current`
   - `git remote -v`
   - Preferred default branch lookup: `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`
   - Fallback default branch lookup: `git remote show origin` and parse `HEAD branch`.
2. Discover the release contract before changing remote state:
   - Search local config first: `.github/workflows`, `.circleci`, `.buildkite`, `render.yaml`, `vercel.json`, `netlify.toml`, `Dockerfile*`, `docker-compose*`, `Makefile`, `Taskfile*`, `package.json`, `pyproject.toml`, `README*`, `docs/**`, `scripts/**`, `bin/**`
   - Search for release terms: `rg -n "staging|preview|prod|production|deploy|health|workflow_dispatch|repository_dispatch|environment|release|promote" ...`
   - Determine the default branch, staging branch/environment, production branch/environment, intermediate environments, deployment triggers, status source, and concrete staging/production health checks.
   - Determine how to verify the intended change on staging and production. Prefer a version/SHA endpoint, deployment metadata, response-body assertion, UI smoke test, or repo-specific command that proves the new behavior is present.
   - If local inspection is insufficient, inspect remote metadata:
     - `gh api repos/{owner}/{repo}/branches --paginate --jq '.[].name'`
     - `gh api repos/{owner}/{repo}/actions/workflows`
     - `gh run list --limit 20 --json databaseId,workflowName,headBranch,headSha,event,status,conclusion,url,createdAt`
     - `gh api repos/{owner}/{repo}/environments`
     - `gh api repos/{owner}/{repo}/deployments?per_page=20`
   - If the release contract is still unclear, stop and ask the user instead of guessing.
3. Collect all local work into one branch and PR:
   - If the current branch has a deleted/unset upstream or its PR is already merged, fetch/rebase onto the default branch and create a fresh `codex/{description}-rebased` branch.
   - If currently on the default branch and there are local changes, create `codex/{description}`.
   - Treat all tracked and untracked files shown by `git status` as part of this single release unless the user explicitly asks for a split.
   - Stage and commit all local work:
     - `git add -A`
     - Commit the full dirty tree. If there are no staged changes, continue without creating a new commit.
   - Push with upstream tracking:
     - `git push -u origin $(git branch --show-current)`
   - Ensure a PR exists. If missing, create one with `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --fill --head $(git branch --show-current)`.
4. Fix PR checks until mergeable:
   - Check status with `gh pr checks`.
   - For failed GitHub Actions jobs, inspect logs via `gh run view <run_id> --log`.
   - Apply fixes locally, commit, push, and re-check.
   - Do not merge while required checks are failing.
5. Merge to the default branch and sync locally:
   - Merge with `gh pr merge --squash --delete-branch`, or the branch-protection-compatible `gh pr merge --auto ...` mode when required.
   - `git checkout <default-branch>`
   - `git pull --ff-only`
   - Keep the merged commit SHA in hand for staging and production verification.
6. Propagate through staging and intermediate environments:
   - If the repository auto-deploys the default branch to staging, wait for that deployment.
   - If staging requires a workflow, provider command, promotion PR, or branch update, trigger the discovered staging path.
   - If there are intermediate environments before production, process them in documented order.
   - Watch the specific workflow run, deployment status, or provider-native status until each environment reaches a terminal success state.
   - Verify each environment reports the merged commit SHA or exact promoted ref.
7. Validate staging before production:
   - Run the discovered staging health checks.
   - Run the staging change-presence checks that prove the intended changes are live.
   - If staging is failing, stale, or serving a different SHA/ref, debug it before production:
     - Inspect workflow logs, deployment events, provider logs, release scripts, and failing smoke-test output.
     - Implement fixes in a new PR/merge cycle using steps 3-5.
     - Re-propagate to staging and repeat staging checks.
8. Promote to production:
   - Use the repo's existing production promotion path. Prefer documented commands and scripts.
   - If the production path is clear but not yet scripted, write a thin reusable script in the repo-native location such as `scripts/` or `bin/`, using existing environment variables/config and no hardcoded secrets, then use that script as the production entrypoint.
   - If production is branch-driven, use the repository's policy: promotion PR when branch protection or review rules exist; direct branch update only when the repo already uses that mechanism and policy permits it.
   - Watch production rollout until the deployment reaches a terminal success state.
   - Verify production reports the merged commit SHA or exact promoted ref.
9. Validate production and loop until truly done:
   - Run production health checks.
   - Run production change-presence checks that prove the intended changes are visible on prod.
   - If production is unhealthy, stale, or missing the intended changes, debug the cause and continue the release loop:
     - Inspect workflow logs, deployment events, provider logs, runtime logs, release scripts, cache/CDN behavior, migrations, feature flags, and smoke-test failures as relevant.
     - Implement fixes in a new PR/merge cycle using steps 3-5.
     - Propagate again through staging/intermediate environments before production.
     - Re-run staging and production rollout, health, and change-presence checks.
   - Do not report success until production is healthy and the intended changes are verified live.
10. Finish with a concise release report:
   - PR number and merge method.
   - Exact deployed SHA/ref.
   - Staging/intermediate and production deployment URLs or workflow run URLs.
   - Health checks and change-presence checks executed.
   - Current `git status --short`.
   - Any policy gate that remains outside Codex control, such as required manual approvals.

## Guardrails

- Do not assume branch names like `staging`, `prod`, `main`, or `master`; discover them from repo config and remote metadata.
- Do not deploy to production before staging and required intermediate environments are healthy and serving the intended SHA/ref.
- Do not bypass branch protections, required reviews, merge queues, deployment approvals, or environment gates.
- Do not hardcode tokens, API keys, or provider-specific secrets into generated scripts.
- Do not force-push or rewrite history unless the user explicitly asks.
- Do not leave the repository dirty at handoff. Under this skill, the expected end state is a clean working tree after production is verified.
- If the repository has no identifiable staging/prod promotion flow, no health checks, or no deployment signal, report that clearly and stop rather than improvising a risky release.
