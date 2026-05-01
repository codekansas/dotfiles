---
name: "code-cleanup"
description: "Align recent commits with CODE_STYLE.md and repo conventions."
---

# Code Cleanup

Use this skill after `CODE_STYLE.md` exists or has just been refreshed.

## Do This First

- Read `CODE_STYLE.md` before changing code.
- Read `references/cleanup-rubric.md`.
- If `CODE_STYLE.md` is missing or obviously stale, stop and run `$init-code-style` first.

## Workflow

1. Define the cleanup window.
   - Prefer a user-provided commit range.
   - Otherwise compare the current branch against its merge-base with the default branch.
   - If that is unclear, inspect the last few commits that introduced the current work.
2. Review recent changes as evidence, not as sacred units.
   - Use `git log --stat`, `git show --name-only`, and `git diff` to see what actually changed.
   - Cluster cleanup work by file, subsystem, or convention drift.
3. Apply style-alignment changes that materially improve the code.
   - module placement
   - naming and exported surface
   - type quality
   - comments and docs
   - test shape
   - logging and error handling
   - config flow and dependency boundaries
4. Preserve intent and behavior.
   - Prefer cleanup that makes the existing change fit the house style.
   - Do not use style cleanup as cover for unrelated rewrites.
5. Validate only what the touched area needs.
   - Run targeted lint, typecheck, tests, or build steps for the affected files.
   - Avoid repository-wide churn unless the user explicitly asks for it.

## Guardrails

- Do not start from generic style opinions; start from `CODE_STYLE.md`.
- Do not touch untouched files unless the cleanup directly improves the modified area.
- Do not rewrite history unless the user explicitly asks.
- Do not perform giant formatting sweeps when the real issue is structural or architectural.
- If `CODE_STYLE.md` conflicts with enforced tooling or established public APIs, follow the real constraint first and call out the mismatch.

## Output Expectations

- The result should feel like the recent work now belongs in the repository.
- Cleanup commits should be focused and explainable.
- When there are remaining mismatches, name them explicitly instead of pretending the branch is fully aligned.
