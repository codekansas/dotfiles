# Manager Repo Pointers

Read when: you need the "how we do it here" details for domains/DNS/redirects.

Assume:

```bash
DOMAIN_OPS_REPO="${DOMAIN_OPS_REPO:-$HOME/Github/manager}"
```

## Files

- `DOMAINS.md`: mappings + registrar quick map + known exclusions/outstanding NS flips.
- `DNS.md`: Cloudflare onboarding checklist + verification steps.
- `redirect-worker.ts`: Worker implementation (fallback redirect behavior).
- `redirect-worker-mapping.md`: host -> target mapping input.
- `bin/namecheap-set-ns`: Namecheap NS flip helper (env vars in `profile` if present).
- `bin/cloudflare-ai-bots`: bot management helper (needs token perms).

## Fast navigation

- Find a domain: `rg -n "\\bexample\\.com\\b" "$DOMAIN_OPS_REPO/DOMAINS.md"`
- List scripts: `ls -la "$DOMAIN_OPS_REPO/bin"`
