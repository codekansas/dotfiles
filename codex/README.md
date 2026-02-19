# Codex Vendor Assets

This directory vendors selected skills and helper scripts adapted from:

- https://github.com/steipete/agent-scripts

Imported on 2026-02-16.

## Included Skills

- `create-cli`
- `domain-dns-ops`
- `frontend-design`
- `instruments-profiling`
- `markdown-converter`
- `native-app-performance`
- `openai-image-gen`
- `oracle`
- `swift-concurrency-expert`
- `swiftui-liquid-glass`
- `swiftui-performance-audit`
- `swiftui-view-refactor`
- `video-transcript-downloader`

## Excluded Skills

- `1password`
- `brave-search`
- `nano-banana-pro`

## Included Scripts

- `scripts/browser-tools.ts`
- `scripts/committer`
- `scripts/docs-list.ts`
- `scripts/shazam-song`
- `scripts/trash.ts`

## Refresh Workflow

1. Clone/fetch upstream `steipete/agent-scripts`.
2. Re-copy the included skills and scripts listed above.
3. Re-apply local portability edits:
   - Remove hardcoded `~/Projects/agent-scripts` paths.
   - Keep `domain-dns-ops` generic via `DOMAIN_OPS_REPO`.
4. Run `rg -n "agent-scripts|~/Projects/manager|steipete\\.md" codex/skills scripts` to verify no personal path leaks.
