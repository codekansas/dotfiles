# Code Style Rubric

Use this rubric to keep `CODE_STYLE.md` verbose, specific, and grounded in the repository.

## Evidence To Gather

- Top-level directories and what each one appears to own.
- Primary languages and their supporting toolchain.
- Lint, format, typecheck, test, build, and deploy config.
- Repeated patterns in representative source files.
- Existing contributor guidance such as `AGENTS.md`, `README*`, `CONTRIBUTING*`, and architecture docs.
- Recent commits that show what the team currently considers acceptable.

## Sections Worth Covering

### 1. Repository Shape

- Which directories are stable public structure versus incidental clutter.
- Where application code, libraries, scripts, tests, docs, and generated artifacts belong.
- How new subsystems should be added without creating another junk drawer.

### 2. Architectural Boundaries

- How dependency flow should move through the repository.
- What belongs in domain logic versus adapters, framework glue, and CLIs.
- How configuration should be represented and where side effects are allowed.

### 3. Language Conventions

- Naming rules, typing expectations, module scope, error handling, and documentation style.
- Which conventions are enforced by tooling versus expected by taste.
- Any repository-specific conventions that matter more than upstream defaults.

### 4. Review Standards

- What "good enough" looks like for tests, logging, migrations, observability, and API stability.
- Which kinds of refactors are encouraged and which are considered churn.
- What to avoid in follow-up commits and cleanup work.

## Observed Versus Aspirational

Use both, but keep them separate.

- Observed: already common, tool-backed, or present in the best-maintained areas.
- Aspirational: preferred direction where the repo is inconsistent.

If a section is aspirational, say that clearly. A misleading style guide is worse than an incomplete one.

## How To Avoid AI Vibe Rules

- Tie major rules to something you actually observed.
- Prefer "use package-first layouts because this repo already organizes code that way" over "modularize for scalability."
- Avoid generic advice that could be pasted into any repository unchanged.
- Avoid recommending abstractions purely because they look sophisticated.
- Avoid rules that maximize apparent polish at the cost of directness.
- Avoid turning temporary codegen or one-off experiments into permanent standards.

## Update Strategy

When `CODE_STYLE.md` already exists:

- Preserve deliberate choices that still make sense.
- Remove stale references and duplicated guidance.
- Reconcile contradictions instead of layering new text on top.
- Keep the voice authoritative and practical, not committee-written.
