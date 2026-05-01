---
name: "security-audit"
description: "Run repository security audits covering code, config, CI/CD, secrets, auth, and deployments."
---

# Security Audit

Audit a repository like an AppSec reviewer, not a lint rule bundle.

## Do This First

- Read `references/audit-rubric.md`.
- If the user did not narrow scope, audit the repository root and say so explicitly.
- Inspect top-level guidance and architecture context first:
  - `AGENTS.md`, `README*`, `docs/`, `CONTRIBUTING*`, deployment notes, and any existing threat model or security docs
  - manifests, lockfiles, CI config, container files, IaC, and environment examples
- Identify the real runtime shape before judging risk:
  - entrypoints
  - authn/authz boundaries
  - secrets and config flow
  - data stores
  - external integrations
  - deployment and build pipeline

## Workflow

1. Build the attack-surface map.
   - Separate runtime surfaces from developer tooling, tests, and examples.
   - List the components that matter for security: public endpoints, background jobs, admin paths, parsers, file uploads, webhooks, CLIs, queues, storage, and third-party services.
   - Note the trust boundaries and where data crosses them.
2. Review the highest-risk categories first.
   - authn/authz and privilege boundaries
   - secrets exposure and unsafe config defaults
   - injection, deserialization, template, and command-execution paths
   - file handling, path traversal, SSRF, and outbound network pivots
   - dependency and supply-chain risk in manifests, lockfiles, and CI
   - deployment, container, and infrastructure misconfiguration
   - tenancy, data isolation, audit logging, and security-sensitive business logic
3. Validate findings before reporting them.
   - Prefer high-confidence findings with a concrete exploit path, unsafe invariant, or clearly dangerous default.
   - Include exact file references and line numbers whenever possible.
   - Separate confirmed findings from assumptions that depend on deployment context.
   - Prefer a short list of real issues over a long list of generic hardening advice.
4. Write the report as a repository artifact.
   - Unless the user specifies otherwise, write `<repo-name>-security-audit.md` at the repo root.
   - Include:
     - executive summary
     - scope and assumptions
     - attack-surface overview
     - findings ordered by severity
     - quick wins
     - deferred hardening ideas that are not findings
5. If the user wants fixes, address one finding cluster at a time.
   - Start with the highest-severity issue that can be fixed safely.
   - Preserve behavior unless the vulnerability requires a behavior change.
   - Re-run the smallest useful validation after each fix.

## Report Expectations

- The report should read like a real security assessment, not a scanner dump.
- Each finding should include:
  - severity
  - short title
  - impacted files or components
  - why it matters
  - evidence
  - recommended remediation
- Name residual uncertainty explicitly instead of padding severity.
- If no concrete vulnerabilities are found, say that directly and list the most important residual risks or review gaps.

## Guardrails

- Do not report generic missing controls with no repository evidence.
- Do not treat every dev-only shortcut as a production vulnerability unless the repo suggests it ships that way.
- Do not confuse "not ideal" with "exploitable."
- Do not inflate third-party package noise into a finding unless the package is actually in use or the vulnerable feature is reachable.
- When severity depends on unknown deployment context, explain the branching logic instead of guessing.

## Output Expectations

- The result should give the user a prioritized security picture of the repository, not just secure-coding trivia.
- Findings should be grounded, defensible, and easy to act on.
- The written report should be concise enough to review, but complete enough to hand to an engineer for remediation work.
