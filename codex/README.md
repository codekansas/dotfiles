# Codex Profiles And Rules

Codex loads `~/.codex/config.toml` first, then `codex -p NAME` overlays
`~/.codex/NAME.config.toml`.

- `default`: durable local workstation defaults from the live config.
- `quick`: lower-reasoning profile for small, fast tasks.
- `deep`: explicit high-effort profile for difficult implementation work.
- `safe`: read-only inspection and review.
- `unattended`: sandboxed workspace writes with no approval prompts.
- `yolo`: full local access with no approval prompts.

`rules/default.rules` is installed as `~/.codex/rules/default.rules`. It keeps
low-risk inspection commands allowed and routes common mutating development
commands through `auto_review`.
