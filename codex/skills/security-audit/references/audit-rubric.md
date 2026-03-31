# Security Audit Rubric

Use this rubric to keep the audit focused on real repository risk rather than generic best-practice drift.

## Evidence To Gather

- Repo shape, deployment model, and intended exposure.
- Entry points: HTTP handlers, RPC, CLIs, jobs, webhooks, admin tools, upload paths, and parsers.
- Authn/authz flow: middleware, policy checks, role mapping, tenant scoping, session handling, API keys, service accounts.
- Secret and config flow: `.env` examples, vault clients, config loaders, CI secrets, credentials in code or history-adjacent files.
- Supply chain surface: manifests, lockfiles, install scripts, custom build steps, CI actions, container base images.
- Infrastructure and runtime config: Dockerfiles, compose, Terraform, Helm, Kubernetes manifests, reverse-proxy config, CDN or edge config.
- Data sensitivity clues: PII, payments, tokens, internal admin features, signing keys, audit logs, model or training artifacts.

## Review Buckets

### 1. Exposure And Trust Boundaries

- What is internet-facing, internal-only, or user-triggerable through another system.
- Where untrusted data crosses into trusted execution.
- Where privilege changes happen.

### 2. Identity And Access Control

- Missing or inconsistent auth checks.
- Broken object- or tenant-level authorization.
- Privileged endpoints reachable from user-controlled flows.
- Unsafe impersonation, role escalation, or shared credentials.

### 3. Input Handling And Code Execution

- SQL, shell, template, path, or query injection.
- Unsafe deserialization or dynamic evaluation.
- File upload or archive extraction bugs.
- SSRF, webhook abuse, or unsafe outbound fetches.

### 4. Secrets And Cryptography

- Hardcoded secrets or credentials in examples that look live.
- Token leakage through logs, URLs, client code, or build artifacts.
- Home-grown crypto or dangerous crypto defaults.
- Missing key separation, rotation hooks, or signing boundaries where the app relies on them.

### 5. Supply Chain And Build Integrity

- Reachable vulnerable packages matter more than stale dependency noise.
- Over-privileged CI tokens, unsafe GitHub Actions patterns, or unpinned third-party actions.
- Install-time scripts, remote curl-pipe-shell flows, or artifact trust gaps.

### 6. Deployment And Runtime Hardening

- Containers running as root without reason.
- Debug, admin, or profiling surfaces exposed by default.
- Overly permissive CORS, proxy trust, network egress, or storage access.
- Missing isolation between environments or tenants.

### 7. Detection And Recovery

- Audit logs missing around privileged actions.
- Error handling that leaks secrets or internal state.
- Weak revocation, lockout, abuse throttling, or incident-response hooks where the system clearly needs them.

## Finding Quality Bar

Before calling something a finding, check:

- Is there concrete repository evidence?
- Is the vulnerable path reachable, or at least plausibly reachable from the documented runtime?
- Is the impact specific?
- Can you point to the exact files and lines?
- Are you reporting a real risk, not just a more secure alternative?

If several weak signals are needed to make the case, write the finding as conditional and explain the assumption clearly.

## Severity Calibration

- Critical: pre-auth RCE, auth bypass, tenant escape, signing-key compromise, or direct exposure of highly sensitive data.
- High: privilege escalation, exploitable secret exposure, impactful SSRF, command execution behind low-friction auth, or CI compromise with production impact.
- Medium: meaningful but constrained data exposure, abuse paths requiring preconditions, weak default isolation, or logging/config patterns likely to create incidents.
- Low: defense-in-depth gaps, noisy or narrow leakage, or hardening work with limited standalone impact.

Prefer lower severity when the exploit path depends on uncertain deployment assumptions. Raise severity only when the repo evidence supports it.

## Report Shape

Use this structure by default:

1. Executive summary
2. Scope and assumptions
3. Attack-surface overview
4. Findings by severity
5. Quick wins
6. Deferred hardening and open questions

For each finding, include:

- ID
- Severity
- Title
- Impact
- Evidence with file references
- Remediation

## Non-Goals

- Dumping every outdated package version without reachability or context.
- Treating missing ideal controls as exploitable by default.
- Rewriting the whole architecture during an audit.
- Reporting speculative issues that cannot be traced back to repository evidence.
