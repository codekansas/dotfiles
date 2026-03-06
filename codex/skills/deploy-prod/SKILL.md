---
name: "deploy-prod"
description: "Use when the user explicitly asks to take a healthy staging deployment all the way to production in one flow: inspect the repository's CI/CD setup, identify how staging and production are deployed, verify staging health, write a reusable production deploy script when the deployment path is clear but not yet scripted, then trigger production and monitor rollout status until production is deployed and healthy."
---

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install `gh` and stop.
- Require authenticated `gh` session. Run `gh auth status`. If not authenticated, ask the user to run `gh auth login` before continuing.
- If the repo depends on a provider CLI such as `vercel`, `netlify`, `wrangler`, `render`, `flyctl`, or `kubectl`, prefer the repo's documented command path. If the required CLI is missing and GitHub alone cannot complete the deploy, ask the user to install or authenticate it and stop.

## Naming Conventions

- Promotion branch when one is required: `codex/deploy-prod-{short-sha}`.
- Commit message when a promotion commit is required: `deploy prod: {staging-ref} -> {prod-ref} @ {short-sha}`.
- PR title when a promotion PR is required: `[codex] deploy prod: {staging-branch} -> {prod-branch} @ {short-sha}`.

## Workflow

1. Discover repository and deployment context:
   - `git status -sb`
   - `git branch --show-current`
   - `git remote -v`
   - `gh repo view --json nameWithOwner,defaultBranchRef,url`
   - Search local config first: `.github/workflows`, `.circleci`, `.buildkite`, `render.yaml`, `vercel.json`, `netlify.toml`, `Dockerfile*`, `docker-compose*`, `Makefile`, `Taskfile*`, `package.json`, `pyproject.toml`, `README*`, `docs/**`, `scripts/**`, `bin/**`
   - Search for deploy and health terms: `rg -n "staging|prod|production|deploy|health|workflow_dispatch|repository_dispatch|environment|release|promote" ...`
2. Identify the release contract:
   - Determine the staging branch or staging environment.
   - Determine the production branch or production environment.
   - Determine which commit or ref is intended for promotion.
   - Determine the exact production trigger path: workflow dispatch, deployment script, provider CLI, promotion PR, or documented branch update.
   - Determine whether a reusable production deploy script already exists.
   - Determine the rollout status source: workflow run, GitHub deployment status, provider CLI output, or documented release script output.
   - Determine concrete staging and production health checks.
   - If any of these remain ambiguous after local inspection, inspect remote metadata:
     - `gh api repos/{owner}/{repo}/branches --paginate --jq '.[].name'`
     - `gh api repos/{owner}/{repo}/actions/workflows`
     - `gh run list --limit 20 --json databaseId,workflowName,headBranch,headSha,event,status,conclusion,url,createdAt`
     - `gh api repos/{owner}/{repo}/environments`
     - `gh api repos/{owner}/{repo}/deployments?per_page=20`
   - If the release contract is still unclear, stop and ask the user instead of guessing.
3. Verify the live staging deployment is the right target:
   - Resolve the current staging branch head: `git ls-remote --heads origin <staging-branch>`
   - Identify the currently deployed staging revision from the repository's deployment system.
   - Confirm the staging deployment corresponds to the commit you intend to promote.
   - If staging is lagging, deploying a different SHA, or actively failing, stop.
4. Run staging health checks before promotion:
   - Prefer the repo's documented smoke tests or health-check commands.
   - If the repo only exposes URLs, use explicit checks such as `curl -fsS`, response-body assertions, or a documented `/health` / `/readyz` endpoint.
   - Require all staging health checks to succeed before moving on.
5. Trigger production using the repo's existing promotion path:
   - If the deployment path is clear but no reusable production deploy script exists yet, write one before deploying:
     - Place it in the repo-native location such as `scripts/` or `bin/`.
     - Follow the repo's existing language and style conventions.
     - Keep it thin: accept the needed ref or environment inputs, call the existing provider CLI / `gh` / repo command, and exit non-zero on failure.
     - Do not hardcode secrets; read existing environment variables or repo config instead.
     - After writing it, use that script as the production entrypoint.
   - If the repo uses a documented deploy command or script, run that exact command.
   - If the repo uses GitHub Actions `workflow_dispatch`, trigger it with `gh workflow run ...` and pass the discovered ref/environment inputs.
   - If production is branch-driven, update the production branch using the repository's policy:
     - Prefer a promotion PR from staging to production when branch protection or review rules exist.
     - If currently on the default or production branch and a promotion branch is needed, create one: `git checkout -b "codex/deploy-prod-{short-sha}"`
     - Push with tracking: `git push -u origin $(git branch --show-current)`
     - Ensure a PR exists for the promotion branch:
       - `gh pr view --json number,state,headRefName,baseRefName`
       - If no PR exists, create one: `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --fill --head $(git branch --show-current)`
     - Wait for required checks and approvals, then merge with `gh pr merge` using the mode that matches branch protection.
     - Only perform a direct branch update when the repository already uses that mechanism and branch protection allows it.
6. Monitor rollout until production reaches a terminal state:
   - Watch the specific workflow run with `gh run watch <run-id>` when Actions drives deployment.
   - Poll deployment statuses or provider-native status commands when Actions is not the source of truth.
   - Keep the expected production commit SHA in hand and verify the deployment reports that exact SHA (or the exact branch head you promoted).
7. Run production health checks after rollout finishes:
   - Re-run the production health checks defined by the repo.
   - Confirm response status, body, and any version/SHA signal the repo exposes.
   - Do not report success until both rollout status and production health checks are green.
8. Report the final state:
   - Production branch/environment updated.
   - Exact deployed SHA.
   - Workflow/deployment URL used for monitoring.
   - Staging and production health checks that were executed.
   - Any remaining manual follow-up if the deployment system finished but policy gates remain.

## Guardrails

- Do not assume branch names like `staging`, `prod`, `main`, or `master`; discover them from the repo and remote metadata.
- Do not deploy if staging health is unknown, failing, or tied to a different commit than the one being promoted.
- Do not bypass branch protections, required reviews, merge queues, or deployment approvals.
- Do not write a production deploy script unless the production trigger path is clear enough to encode safely.
- Do not hardcode tokens, API keys, or provider-specific secrets into a generated deploy script.
- Do not force-push or rewrite history unless the user explicitly asks.
- Do not stop after triggering production; wait for deployment completion and production health checks.
- If the repository has no identifiable staging/prod promotion flow, no health checks, or no deployment signal, report that clearly and stop rather than improvising a risky release.
