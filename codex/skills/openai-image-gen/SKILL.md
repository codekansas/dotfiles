---
name: openai-image-gen
description: "Batch-generate OpenAI Images with random prompts and an HTML gallery."
---

# OpenAI Image Gen

Generate a handful of “random but structured” prompts and render them via OpenAI Images API.

## Setup

- Needs env: `OPENAI_API_KEY`

## Run

From any directory (outputs to `~/Projects/tmp/...` when present; else `./tmp/...`):

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/openai-image-gen/scripts/gen.py"
open ~/Projects/tmp/openai-image-gen-*/index.html
```

Useful flags:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/openai-image-gen/scripts/gen.py" --count 16 --model gpt-image-1.5
python3 "${CODEX_HOME:-$HOME/.codex}/skills/openai-image-gen/scripts/gen.py" --prompt "ultra-detailed studio photo of a lobster astronaut" --count 4
python3 "${CODEX_HOME:-$HOME/.codex}/skills/openai-image-gen/scripts/gen.py" --size 1536x1024 --quality high --out-dir ./out/images
```

## Output

- `*.png` images
- `prompts.json` (prompt ↔ file mapping)
- `index.html` (thumbnail gallery)
