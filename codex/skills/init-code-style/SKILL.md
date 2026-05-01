---
name: "init-code-style"
description: "Create or refresh repo CODE_STYLE.md from code, docs, tooling, and architecture."
---

# Init Code Style

Create or update `CODE_STYLE.md` as a repository manual, not a generic template.

## Do This First

- Read `references/code-style-rubric.md`.
- Inspect the repository before drafting anything:
  - top-level guidance such as `AGENTS.md`, `README*`, `CONTRIBUTING*`, `docs/`, and any existing `CODE_STYLE.md`
  - top-level structure with `rg --files`, `find`, and representative directories
  - tool-enforced conventions from manifests and config files: linters, formatters, typecheckers, test runners, CI, deployment, build, and package management
  - representative source files, tests, scripts, and entrypoints in each major subsystem

## Workflow

1. Build an evidence-backed repository snapshot.
   - Identify primary languages, frameworks, and build tools.
   - Map the main directory boundaries and what belongs in each one.
   - Note repeated patterns that already appear in the strongest parts of the codebase.
2. Separate observed rules from aspirational rules.
   - Observed rules are already common, enforced by tooling, or clearly preferred in high-quality files.
   - Aspirational rules are useful direction but not yet universal.
   - Label aspirational guidance honestly instead of pretending it is already standard.
3. Write `CODE_STYLE.md` as a verbose, operational guide.
   - Cover repository layout, architecture boundaries, naming, module structure, typing, state flow, testing, logging, docs, and change hygiene.
   - Include repository-shape guidance, not just local syntax rules.
   - Explain the "why" for rules that are not obvious from tooling alone.
4. Keep the document specific to the repo.
   - Prefer concrete guidance such as "CLI entrypoints stay thin and delegate into `src/...` packages" over empty slogans such as "keep code maintainable."
   - Mention example paths or file families when they help anchor a rule.
5. When updating an existing file, preserve deliberate human choices.
   - Tighten stale sections, merge duplicates, and remove contradictions.
   - Do not bulldoze a hand-written guide just to make it look uniform.

## What `CODE_STYLE.md` Should Usually Contain

- Repository purpose and design taste.
- Directory layout and dependency direction.
- Language-specific rules for the languages actually present.
- Boundaries between domain logic, infrastructure, framework glue, and scripts.
- Naming, file organization, and public API guidance.
- Testing expectations and what is worth validating.
- Logging, error-handling, and configuration rules.
- Review checklist and "avoid this" guidance for the repository.

## Anti-Patterns To Avoid

- Do not cargo-cult common AI code habits into the guide:
  - pointless abstraction layers
  - tiny helpers split across too many files
  - generic `utils` buckets without ownership
  - style rules that optimize for looking polished instead of matching the repo
  - blanket "make everything reusable/configurable" guidance
- Do not overfit to one unusually clean file if the wider repository uses a different pattern.
- Do not turn unresolved architecture disagreements into fake hard rules.
- Do not fill the document with obvious advice that has no repository-local consequence.

## Output Expectations

- The file should be detailed enough that a new contributor or agent can use it as the default house style.
- The document should read as a real engineering manual, not an AI-generated checklist.
- If the repo lacks clear standards in an area, say so and provide a careful recommendation instead of pretending certainty.
