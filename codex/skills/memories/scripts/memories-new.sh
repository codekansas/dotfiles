#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/memories-common.sh"

title=""
status="inbox"
tags_csv=""
paths_csv=""
body_text=""
custom_id=""
open_in_editor=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)
      title="${2:-}"
      shift 2
      ;;
    --status)
      status="${2:-}"
      shift 2
      ;;
    --tags)
      tags_csv="${2:-}"
      shift 2
      ;;
    --paths)
      paths_csv="${2:-}"
      shift 2
      ;;
    --body)
      body_text="${2:-}"
      shift 2
      ;;
    --id)
      custom_id="${2:-}"
      shift 2
      ;;
    --editor)
      open_in_editor=1
      shift
      ;;
    *)
      printf 'usage: memories-new.sh --title "..." [--status inbox|active|archive] [--tags a,b] [--paths path/to/file] [--body "..."] [--id custom-id] [--editor]\n' >&2
      exit 1
      ;;
  esac
done

if [[ -z "$title" ]]; then
  printf 'memories: --title is required\n' >&2
  exit 1
fi

ensure_memories_layout

status="$(normalize_status "$status")"
tags_csv="$(normalize_tags "$tags_csv")"
paths_csv="$(normalize_paths "$paths_csv")"

if [[ -z "$body_text" && ! -t 0 ]]; then
  body_text="$(cat)"
fi

memory_slug="$(safe_slug "$title")"
if [[ -n "$custom_id" ]]; then
  memory_id="$(safe_slug "$custom_id")"
else
  memory_id="$(timestamp_id)-${memory_slug}"
fi
created_at="$(now_utc)"

if [[ -n "$custom_id" ]]; then
  memory_path="$(memory_target_path "$status" "$memory_id")"
  if [[ -e "$memory_path" ]]; then
    printf 'memories: memory id already exists: %s\n' "$memory_id" >&2
    exit 1
  fi
else
  memory_id="$(ensure_unique_memory_id "$status" "$memory_id")"
  memory_path="$(memory_target_path "$status" "$memory_id")"
fi

cat >"$memory_path" <<EOF
---
id: ${memory_id}
slug: ${memory_slug}
title: ${title}
status: ${status}
created_at: ${created_at}
updated_at: ${created_at}
tags: ${tags_csv}
paths: ${paths_csv}
---

${body_text}
EOF

"${script_dir}/memories-organize.sh" --quiet

if [[ "$open_in_editor" -eq 1 ]]; then
  "${EDITOR:-vi}" "$memory_path"
  "${script_dir}/memories-organize.sh" --quiet
fi

printf '%s\n' "$(resolve_memory "$memory_id")"
