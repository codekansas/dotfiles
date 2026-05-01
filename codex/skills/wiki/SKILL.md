---
name: wiki
description: "Maintain repo-local `.wiki/` knowledge pages for durable project context."
---

# Repo Wiki

Use this skill proactively to keep a repository's `.wiki/` growing in the background as a local-first LLM-maintained wiki.

The wiki lives under `.wiki/` at the repository root. Raw sources stay immutable, the wiki pages are the compiled knowledge layer, and `index.md` plus `log.md` provide navigation and chronology. Treat the wiki as a passive memory and synthesis layer that compounds over time, so Codex keeps getting better at interpreting the user's questions and intent instead of re-deriving everything from raw documents on every query.

## Layout

Bootstrap the wiki with:

```bash
codex/skills/wiki/scripts/wiki.sh init
```

This creates and maintains:

- `.wiki/raw/` for immutable local source copies when the user wants them stored inside the wiki
- `.wiki/pages/` for generated wiki pages
- `.wiki/pages/overview.md` for the evolving top-level synthesis
- `.wiki/index.md` as the content-oriented catalog
- `.wiki/log.md` as the append-only activity timeline
- `.wiki/.gitignore` plus `/.wiki/` in `.git/info/exclude` so the wiki stays local by default

The helper CLI also supports:

```bash
codex/skills/wiki/scripts/wiki.sh reindex
codex/skills/wiki/scripts/wiki.sh lint
codex/skills/wiki/scripts/wiki.sh log --kind ingest --title "Source title"
```

## Page Conventions

Keep wiki pages as ordinary Markdown files with standard relative Markdown links. Avoid Obsidian-only `[[wikilinks]]`; the helper tools lint standard links directly.

Each page should start with compact frontmatter:

```md
---
title: Example Title
type: concept
summary: One-line summary used by index.md.
updated_at: 2026-04-04T22:00:00Z
source_count: 3
---
```

Required fields:

- `title`
- `type`
- `summary`
- `updated_at`

Common page types:

- `overview`
- `source`
- `entity`
- `concept`
- `analysis`
- `question`
- `note`

Prefer hyphen-case filenames and stable paths such as:

- `.wiki/pages/sources/source-slug.md`
- `.wiki/pages/entities/entity-name.md`
- `.wiki/pages/concepts/topic-name.md`
- `.wiki/pages/analyses/analysis-slug.md`

## Workflow

### 1. Bootstrap

- Run `codex/skills/wiki/scripts/wiki.sh init` if `.wiki/` does not exist.
- Use the wiki passively during normal work. Do not wait for a dedicated "let's build the wiki" request if durable project context is clearly accumulating.
- Read `.wiki/index.md` before doing non-trivial wiki work so you know what already exists.
- Treat `.wiki/raw/` as immutable once a source is stored there.

### 2. Ingest

When new source material appears during ongoing work, or when the conversation reveals durable context worth preserving:

1. Read the source.
2. Create or update a source page under `.wiki/pages/sources/`.
3. Update the relevant entity, concept, and overview pages.
4. Preserve contradictions instead of silently overwriting them.
   Add the newer claim, note the disagreement, and cite both sides.
5. Rebuild the index:

```bash
codex/skills/wiki/scripts/wiki.sh reindex
```

6. Append a log entry:

```bash
codex/skills/wiki/scripts/wiki.sh log \
  --kind ingest \
  --title "Source title" \
  --summary "What changed in the wiki" \
  --pages pages/sources/source-slug.md,pages/concepts/topic-name.md
```

Default to ingesting one source at a time unless the user explicitly asks for batch ingestion.

### 3. Query

When the user asks a question and the wiki is relevant:

1. Read `.wiki/index.md` first.
2. Read the most relevant pages, then answer from the compiled wiki.
3. Cite the wiki pages you used in the answer when the user would benefit from it.
4. If the query produces durable work product or clarifies what the user is really trying to build, file it back into `.wiki/pages/analyses/` instead of leaving it only in chat history.
5. After creating or materially updating an analysis page, run `reindex` and append a `query` log entry.

### 4. Lint

Run the structural lint pass periodically, not only when explicitly asked:

```bash
codex/skills/wiki/scripts/wiki.sh lint
```

The helper checks for:

- missing frontmatter fields
- broken relative Markdown links
- orphan pages with no inbound links

After the structural pass, do a semantic maintenance pass yourself:

- look for contradictions that are not called out clearly
- look for stale claims that newer sources supersede
- look for concepts that deserve their own page
- look for weak cross-references and synthesis gaps
- identify promising follow-up questions or sources

If you repair pages, run `reindex` and append a `lint` log entry.

## Guardrails

- Limit writes to `.wiki/` unless the user explicitly asks to store sources somewhere else.
- Do not modify raw files under `.wiki/raw/` after they are ingested.
- Do not let `.wiki/index.md` and `.wiki/log.md` drift. Rebuild the index and append the log after meaningful wiki changes.
- Prefer incremental edits over full-page rewrites when the existing wiki contains useful human-authored structure.
- If the repo already contains a human-maintained wiki or notes system, adapt to it instead of forcing a second taxonomy on top of it.
