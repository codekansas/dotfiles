---
name: domain-dns-ops
description: >
  Domain/DNS ops across Cloudflare, DNSimple, and Namecheap. Use for onboarding
  zones to Cloudflare, flipping nameservers, setting redirects
  (Page Rules/Rulesets/Workers), updating redirect-worker mappings, and
  verifying DNS/HTTP. Source of truth should be your infrastructure manager
  repository.
---

# Domain/DNS Ops

Use this skill as a thin router to your own infra runbooks and scripts.

## Source of truth (read first)

Set the manager repo path once per session:

```bash
DOMAIN_OPS_REPO="${DOMAIN_OPS_REPO:-$HOME/Github/manager}"
```

Then read:

- `$DOMAIN_OPS_REPO/DOMAINS.md` (domain -> target map; registrar hints; exclusions)
- `$DOMAIN_OPS_REPO/DNS.md` (Cloudflare onboarding + DNS/redirect checklist)
- `$DOMAIN_OPS_REPO/redirect-worker.ts` + `$DOMAIN_OPS_REPO/redirect-worker-mapping.md` (worker redirects)

## Golden path (new vanity domain -> Cloudflare -> redirect)

1. **Decide routing model**
   - Page Rule redirect (small scale, per-zone).
   - Rulesets / Bulk Redirects (account-level; needs token perms).
   - Worker route (fallback; uses `redirect-worker`).
2. **Cloudflare zone**
   - Create zone (UI), then confirm with `cli4`:
     - `cli4 --get name=example.com /zones`
3. **Nameservers**
   - If registrar = Namecheap and helper exists:
     - `cd "$DOMAIN_OPS_REPO" && source profile && bin/namecheap-set-ns example.com emma.ns.cloudflare.com scott.ns.cloudflare.com`
   - If registrar = DNSimple: follow your runbook notes in `$DOMAIN_OPS_REPO/DNS.md`.
4. **DNS placeholders (so CF can terminate HTTPS)**
   - Proxied apex `A` + wildcard `A` -> `192.0.2.1` (see `$DOMAIN_OPS_REPO/DNS.md` for exact `cli4` calls).
5. **Redirect**
   - If using Page Rules: use the `cli4 --post ... /pagerules` template from `$DOMAIN_OPS_REPO/DNS.md`.
   - If using Worker: update mapping (`$DOMAIN_OPS_REPO/redirect-worker-mapping.md`), then deploy/bind routes per `$DOMAIN_OPS_REPO/DNS.md`.
6. **Verify**
   - DNS: `dig +short example.com @1.1.1.1` (expect CF anycast).
   - HTTPS redirect: `curl -I https://example.com` (expect `301`).

## Common ops

- **Cloudflare token sanity**: `source ~/.profile` (prefer `CLOUDFLARE_API_TOKEN`; `CF_API_TOKEN` fallback).
- **Disable “Block AI bots”**: if your manager repo has a helper, run it from `$DOMAIN_OPS_REPO/bin/cloudflare-ai-bots`.

## After edits (commit/push)

If you changed anything in your manager repo (docs, worker, scripts, mappings): commit there too.

1. Review: `cd "$DOMAIN_OPS_REPO" && git status && git diff`
2. Stage: `git add <paths>`
3. Commit (Conventional Commits): `git commit -m "feat: …"` / `fix:` / `docs:` / `chore:`
4. Push only when explicitly asked: `git push origin main`

## Guardrails

- Don’t touch unrelated domains or policy files unless explicitly asked.
- Confirm registrar before debugging CF “invalid nameservers” (often “wrong registrar”).
- Prefer reversible steps; verify after each change (NS → DNS → redirect).
