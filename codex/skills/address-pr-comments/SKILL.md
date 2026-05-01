---
name: "address-pr-comments"
description: "Address unresolved GitHub PR comments end-to-end: patch, push, and resolve handled threads."
---

# Address PR Comments

Use this skill when the user wants GitHub pull request comments handled end to end.

## Prerequisites

- Require GitHub CLI `gh`. Check `gh --version`. If missing, ask the user to install it and stop.
- Require an authenticated `gh` session. Run `gh auth status`. If it fails, ask the user to run `gh auth login` before continuing.
- Prefer the pull request attached to the current branch unless the user provides a PR number or URL.

## Workflow

1. Resolve the target PR.
   - Accept a PR URL, PR number, or current-branch PR.
   - Use `./scripts/pr_review_threads.py fetch --json` for thread-aware review data.
2. Separate real work from noise.
   - Treat unresolved review threads as the primary source of actionable feedback.
   - Ignore approvals, outdated threads, duplicates, and comments that do not require a code or written response.
3. Confirm scope only when needed.
   - If the user asks to address all comments, treat all unresolved actionable threads as in scope.
   - If the user has not asked for blanket cleanup, summarize numbered threads and confirm which ones to handle.
4. Implement the requested fixes locally.
   - Keep each change traceable to one or more review threads.
   - If a comment needs explanation instead of code, draft that explanation rather than forcing a cosmetic patch.
5. Validate the touched areas.
   - Run targeted tests, lint, and typechecks for the files you changed.
6. Commit and push the fixes.
   - Stage only the intentional changes.
   - Use a commit message that describes the actual fix, not a generic "address comments" message.
   - Push the current branch before resolving any threads.
7. Resolve only the threads that are truly addressed.
   - Use `./scripts/pr_review_threads.py resolve <thread-id> ...`.
   - Leave threads open when they still need reviewer judgment, policy clarification, or a written reply.

## Guardrails

- Do not resolve threads before the fix is committed and pushed.
- Do not resolve comments that were answered with "I think this is fine" unless the user explicitly wants that.
- Do not assume flat PR comments capture thread state; always use the review-thread script when resolution state matters.
- Do not mark a thread resolved if the code change only partially addresses it.
- If GitHub auth or API access breaks mid-run, stop and ask the user to re-authenticate.

## Script Notes

`./scripts/pr_review_threads.py` supports two subcommands:

- `fetch`: prints unresolved review threads by default, plus PR metadata, top-level comments, and review bodies
- `resolve`: resolves one or more review thread ids through GitHub GraphQL
