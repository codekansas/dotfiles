# Dotfiles Code Style

This repository is not a single application. It is a curated working environment:

- top-level dotfiles linked into `$HOME`
- shell startup and interactive ergonomics
- small utility scripts
- configuration trees for specific tools
- Codex skills and templates
- a mix of first-party files and vendored or submodule-managed code

That shape matters more than generic style advice. Good changes in this repo preserve directness, keep the install story obvious, and respect the boundary between local curation and upstream-owned code.

## Status Of This Guide

This file intentionally mixes two kinds of guidance:

- Observed: patterns that are already visible in the current repository and should usually be preserved
- Recommended: standards for new or heavily edited code, especially where the existing repo is older, inconsistent, or partly vendored

When observed and recommended guidance conflict, use judgment:

1. preserve working user-facing behavior
2. preserve upstream or vendored code boundaries
3. prefer the recommended style for new first-party code
4. avoid sweeping cleanup unless the user asked for it

## Repository Identity

The repository has a few strong traits that should shape almost every edit:

- The root is intentionally flat because many entries map directly to files in `$HOME`, such as `zshrc`, `gitconfig`, `vimrc`, and `tmux.conf`.
- Installation is driven by DotBot through [`install`](./install) and [`install.conf.yaml`](./install.conf.yaml). The link map is part of the repository's public structure, not incidental glue.
- Shell configuration is a first-class part of the repo. `shell/`, `bash/`, `zsh/`, `cron/`, and top-level startup files are not peripheral.
- Several large areas are vendored or submodule-backed: `dotbot/`, `dotbot-crontab/`, `vim_runtime/`, `vim/bundle/`, `tmux/plugins/`, `zsh/plugins/`, and parts of `third-party/`.
- Python and TypeScript exist mainly to support utilities, templates, and automation, not to form a single monorepo application.

The repository should continue to feel hand-built and intentional. Avoid turning it into a framework or a generalized platform unless there is a very strong reason.

## Directory Map And Ownership

Use the existing directory structure as the default organizing principle.

### Top-Level Files

Top-level files usually represent user-facing dotfiles or root-level repo controls:

- shell entrypoints such as `zshrc`, `bashrc`, `profile`, and `bash_profile`
- tool configs such as `gitconfig`, `condarc`, `curlrc`, `inputrc`, and `tmux.conf`
- repo controls such as `README.md`, `AGENTS.md`, `.gitmodules`, `pyproject.toml`, and `install.conf.yaml`

Preferred rule:

- If a file is conceptually "the file that ends up in `$HOME`", keeping it at the repo root is correct.
- Do not move a root-level dotfile into a nested directory just to make the tree look more abstract.

### Directory Conventions

The first-party directories have clear responsibilities:

- `shell/`: shell-agnostic helpers and environment setup shared across shells
- `bash/`: Bash-specific aliases, prompt, settings, and completion
- `zsh/`: Zsh-specific aliases, completion, settings, plugin orchestration
- `cron/`: scheduled maintenance and automation entrypoints
- `cron-local/`: local integration points that are linked into the home directory
- `config/`: XDG-style config trees such as `config/ghostty` and `config/zellij`
- `python/`: Python helpers, startup files, and the reusable project template
- `scripts/`: executable utilities and one-off tools that warrant a command-style interface
- `codex/`: Codex configuration and local skill content
- `ssh/`: SSH config and include fragments

Recommended rule:

- Put new content where a future reader would naturally look for it first.
- Prefer a directory that maps to a real tool or runtime over a broad category like `misc`, `common`, or `utils`.

### Vendored And Submodule Areas

The following areas are not normal first-party style sources:

- `dotbot/`
- `dotbot-crontab/`
- `vim_runtime/`
- `vim/bundle/`
- `tmux/plugins/`
- `zsh/plugins/`
- `third-party/diff-so-fancy`

Rules for these areas:

- Treat upstream structure as authoritative.
- Avoid reformatting or renaming files to match local taste.
- Make the smallest portability or integration edit that solves the actual problem.
- Prefer updating the upstream source or submodule reference over building a large local divergence.
- If you must patch vendored code, keep the patch narrow and explain why in the commit or PR.

Submodule-backed code is not the right place to infer house style for new first-party work.

## Installation And Link Management

[`install.conf.yaml`](./install.conf.yaml) is one of the most important files in the repository. It expresses how repo content maps into the user's machine.

Observed patterns:

- Link destinations are declared explicitly and grouped by tool or area.
- `create` and `relink` are enabled globally.
- install-time shell commands are concise and operational rather than abstracted away.
- cron setup is declared in DotBot config rather than hidden in ad hoc scripts.

Rules:

- When adding a new first-party file or directory that must appear in `$HOME`, update `install.conf.yaml` in the same change.
- Keep the link map readable. Group related entries together and preserve the existing shape of the file.
- Prefer explicit link entries over clever indirection.
- If a file should not be installed automatically, do not add it to the link map just because it exists in the repo.
- Installer logic belongs in DotBot config or the root `install` entrypoint, not scattered across unrelated startup files.

Do not make the bootstrap story harder to inspect than it already is.

## Shell And Dotfile Style

Shell code is central to this repository. The right style is usually simple, direct, and fast to read.

### Sourceable Shell Files

Files in `shell/`, `bash/`, and `zsh/` are often sourced into interactive sessions.

Rules:

- Keep sourced files idempotent and cheap to run.
- Prefer direct environment setup, aliases, bindings, and small helper functions.
- Use comments to separate logical blocks, not to narrate every line.
- Preserve shell-specific idioms when they are natural for the file being edited.
- Avoid heavy startup work in interactive init files unless the user benefit is immediate and clear.

Observed style:

- many functions are short and procedural
- comments are sparse but useful
- shell blocks are grouped by concern
- naming is pragmatic rather than overdesigned

### Executable Shell Scripts

Standalone executables in `scripts/`, `cron/`, or top-level entrypoints should be more disciplined than sourced snippets.

Rules:

- Always use an explicit shebang.
- Use strict mode when it is safe for the script's semantics. `set -euo pipefail` is appropriate for many standalone utilities; it is not appropriate to cargo-cult into every sourced shell fragment.
- Validate arguments early for user-facing commands.
- Quote variables unless there is a deliberate reason not to.
- Prefer a few named functions over a giant inline script body when the script does more than one thing.
- Keep user-visible output short and useful.

Do not build shell frameworks here. Most scripts should remain easy to inspect in one screen or a few screens.

## Utility Scripts

The `scripts/` directory is for commands, not for internal libraries pretending to be a package.

Observed patterns:

- scripts are executable
- some are shell, some are Python, some are Node/TypeScript
- many tools are self-contained and optimized for direct use from the terminal
- wrappers may bootstrap their own runtime dependencies when necessary

Rules:

- Default to a single self-contained executable when the tool is narrow in scope.
- Only split code into helper files when it materially improves readability or reuse.
- Keep runtime assumptions explicit. For example, if a script requires `node`, `uv`, `npm`, or a browser binary, make that obvious in the script or adjacent documentation.
- Prefer local clarity over cross-script abstraction.
- Avoid introducing a repo-wide package manager workspace for one utility.

If a script grows into a reusable subsystem with multiple modules and tests, move it toward a proper package layout instead of leaving it as a pile of shell glue.

## Python Style

New first-party Python should follow the repository's current human guidance, not the loosest historical code in the tree.

### What Counts As Normative

Use these as the primary style sources for new Python:

- [`AGENTS.md`](./AGENTS.md)
- [`python/template/pyproject.toml`](./python/template/pyproject.toml)
- the package-first recommendations in the repository prompt and this document

Do not infer Python style from vendored code in `dotbot/` or `dotbot-crontab/`.

### Structure

Rules:

- Small single-file scripts are fine for narrow tasks in `python/` or `scripts/`.
- Reusable or growing Python logic should move toward a package-first layout modeled after `python/template/`.
- Keep entrypoints thin: parse arguments, resolve inputs, call library code, print or write results.
- Separate durable logic from environment-specific I/O when the script is more than trivial.
- Avoid catch-all helper modules.

### Typing And APIs

Rules:

- Target modern Python and use built-in type syntax such as `list[str]` and `dict[str, int]`.
- Prefer explicit types over `Any`.
- Use Protocols or ABCs when multiple implementations are expected.
- Treat `__init__.py` exports as intentional when building reusable packages.
- Use clear argument names; prefer descriptive loop variables over one-letter names.

### Style And Documentation

Rules:

- Follow Google's Python style guide as the default.
- Use docstrings for genuinely complex functions and modules, especially when behavior is not obvious from the code.
- Do not pad simple code with redundant comments.
- Use `logger = logging.getLogger(__name__)` for nontrivial programs instead of sprinkling `print`.
- Keep comments focused on intent, invariants, or tricky mechanics.

### Tooling

Observed state:

- the root [`pyproject.toml`](./pyproject.toml) configures Black, Ruff, and pytest with a relatively light rule set
- the Python project template uses stricter Ruff settings and includes `ty`

Recommended rule:

- For new first-party Python, treat the stricter template and `AGENTS.md` guidance as the target.
- Run `ruff check` and `ty lint` when the tools are available.
- Add targeted pytest coverage only when there is real logic worth locking down.

In other words: existing repo tooling is the minimum floor, not the quality ceiling.

## TypeScript And JavaScript Style

This repository does not currently act like a typical web app monorepo. JavaScript and TypeScript are used mainly for standalone tools.

Observed patterns:

- modern Node imports
- CLI-oriented scripts
- minimal packaging overhead
- direct file system and process APIs
- TypeScript executed with runtime helpers rather than a repo-wide build graph

Rules:

- Prefer modern Node and ESM-style imports for new TS/JS utilities.
- Keep dependencies narrow and justified.
- Favor direct, readable control flow over framework-heavy structure.
- Prefer `const x = ...` over `function x(...)` for new JavaScript or TypeScript helpers unless the surrounding file already uses function declarations heavily and matching local style is more readable.
- Keep scripts self-contained. If a helper file is needed, it should have a clear ownership boundary rather than acting as a generic shared bucket.

If a change is actually building a web-facing application rather than a utility script, Vercel-friendly defaults are reasonable, but that is not the current center of gravity of this repo.

## Configuration Files

A large part of the repository consists of configuration files that humans edit directly.

Rules:

- Preserve readability and hand-editability.
- Do not reorder keys or rewrite formatting unless that improves clarity or is required by the format.
- Preserve comments when they carry real operational meaning.
- Prefer explicit configuration over generated configuration.
- Match the conventions of the target format: TOML should stay clean, YAML should stay obvious, JSON should stay compact and unsurprising.

For config trees under `config/`, mirror the structure expected by the target application instead of imposing a repo-internal abstraction layer.

## Codex Skills And Codex Config

The `codex/` tree is first-party content, but it has its own stable structure.

Observed patterns:

- `codex/config_template.toml` is a plain, human-editable template
- skills live under `codex/skills/<skill-name>/`
- each skill is centered on `SKILL.md`
- optional skill resources live in predictable subdirectories such as `agents/`, `references/`, `scripts/`, and `assets/`
- install wiring is handled by `install.conf.yaml`

Rules:

- Keep each skill directory focused on one capability.
- Put durable guidance in `SKILL.md`.
- Add helper scripts or references only when they materially improve reliability or keep the skill body small.
- Use `agents/openai.yaml` only for UI-facing metadata, not as a dumping ground for extra instructions.
- When vendoring or adapting skills from elsewhere, preserve provenance where it exists and keep local portability edits narrow.

Do not let `codex/skills/` turn into a random notes directory.

## Documentation Style

The root [`README.md`](./README.md) is intentionally concise. It introduces installation and a handful of user-facing commands without trying to become a complete manual.

Rules:

- Keep the root README short and practical.
- Put specialized documentation near the code or template it explains.
- Add new docs when behavior is non-obvious, but avoid spinning up extra prose files for every small change.

Recommended if a future top-level `docs/` tree is introduced:

- use short front matter with at least a `summary`
- include `read_when` hints if the documentation is meant to be surfaced by tools like `scripts/docs-list.ts`

That recommendation is aspirational; the current repo does not yet depend on a central docs tree.

## Validation And Testing

Validation in this repo should match the kind of artifact being changed.

### For Shell And Config Changes

- run the narrowest syntax or smoke check that actually exercises the change
- use `bash -n` or `zsh -n` for standalone shell syntax when appropriate
- manually source or execute the relevant command path when behavior is interactive
- avoid claiming validation you did not actually perform

### For Python Changes

- run `ruff check` and `ty lint` when available
- run targeted pytest coverage for real logic
- smoke-test CLI entrypoints with `--help` or a representative small invocation

### For TypeScript And JavaScript Changes

- run the script or CLI directly
- validate `--help` paths and a representative success path
- keep runtime bootstrap behavior working if the script installs or locates its own dependencies

### For Installer Changes

- verify that `install.conf.yaml` still reads clearly
- check that new link paths are correct on both repo and destination sides
- if practical, run the relevant DotBot path rather than assuming the mapping is correct

This repo does not need maximal test coverage. It does need honest, targeted validation.

## Change Hygiene

Good changes in this repository are usually narrow and legible.

Rules:

- Change the smallest coherent surface that solves the real problem.
- Avoid repo-wide style churn, especially in dotfiles and vendored directories.
- Do not "clean up" unrelated files while touching a config or script unless the user asked for cleanup.
- Keep naming and directory placement boring and obvious.
- Update installation mapping, templates, or adjacent docs in the same change when required by behavior.

When adding new conventions, prefer to encode them in templates or the repository guide rather than relying on memory.

## Things To Avoid

These are especially important in this repo:

- generic `utils` directories with fuzzy ownership
- large abstraction layers around simple shell or config behavior
- moving root-level dotfiles into nested trees to satisfy abstract aesthetics
- heavy framework scaffolding for a one-file script
- sweeping edits inside submodules or vendored trees
- style rewrites that erase helpful comments or hand-tuned ordering
- AI-looking "platformization" of a repo that currently works because it is direct

## Default Decision Rule

When you are unsure how to structure a change, choose the option that:

1. keeps the install story obvious
2. preserves the direct mapping between repo content and machine behavior
3. respects vendored boundaries
4. keeps first-party code small, explicit, and easy to inspect
5. upgrades quality for new work without forcing a cosmetic rewrite of older working files

That is the house style of this repository.
