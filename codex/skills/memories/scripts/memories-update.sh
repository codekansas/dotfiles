#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/memories-common.sh"

selector=""
title=""
status=""
tags_csv=""
paths_csv=""
add_tags_csv=""
add_paths_csv=""
note_text=""
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
    --add-tags)
      add_tags_csv="${2:-}"
      shift 2
      ;;
    --add-paths)
      add_paths_csv="${2:-}"
      shift 2
      ;;
    --note)
      note_text="${2:-}"
      shift 2
      ;;
    --editor)
      open_in_editor=1
      shift
      ;;
    -*)
      printf 'usage: memories-update.sh <memory-id-or-path> [--title "..."] [--status inbox|active|archive] [--tags a,b] [--add-tags a,b] [--paths path/to/file] [--add-paths path/to/file] [--note "..."] [--editor]\n' >&2
      exit 1
      ;;
    *)
      if [[ -z "$selector" ]]; then
        selector="$1"
        shift
      else
        printf 'memories: unexpected argument: %s\n' "$1" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$selector" ]]; then
  printf 'memories: supply a memory id or path\n' >&2
  exit 1
fi

ensure_memories_layout

memory_path="$(resolve_memory "$selector")"
memory_id="$(read_meta id "$memory_path" || true)"
if [[ -z "$memory_id" ]]; then
  memory_id="$(basename "$memory_path" .md)"
fi

if [[ -n "$title" ]]; then
  set_meta title "$title" "$memory_path"
  set_meta slug "$(safe_slug "$title")" "$memory_path"
fi

if [[ -n "$status" ]]; then
  set_meta status "$(normalize_status "$status")" "$memory_path"
fi

if [[ -n "$tags_csv" ]]; then
  set_meta tags "$(normalize_tags "$tags_csv")" "$memory_path"
fi

if [[ -n "$add_tags_csv" ]]; then
  current_tags="$(read_meta tags "$memory_path" || true)"
  merged_tags="$(merge_csv "$(normalize_tags "$current_tags")" "$(normalize_tags "$add_tags_csv")")"
  set_meta tags "$merged_tags" "$memory_path"
fi

if [[ -n "$paths_csv" ]]; then
  set_meta paths "$(normalize_paths "$paths_csv")" "$memory_path"
fi

if [[ -n "$add_paths_csv" ]]; then
  current_paths="$(read_meta paths "$memory_path" || true)"
  merged_paths="$(merge_csv "$(normalize_paths "$current_paths")" "$(normalize_paths "$add_paths_csv")")"
  set_meta paths "$merged_paths" "$memory_path"
fi

if [[ -z "$note_text" && ! -t 0 ]]; then
  note_text="$(cat)"
fi

if [[ -n "$note_text" ]]; then
  {
    printf '\n## %s\n\n' "$(now_utc)"
    printf '%s\n' "$note_text"
  } >>"$memory_path"
fi

set_meta updated_at "$(now_utc)" "$memory_path"

if [[ "$open_in_editor" -eq 1 ]]; then
  "${EDITOR:-vi}" "$memory_path"
  set_meta updated_at "$(now_utc)" "$memory_path"
fi

"${script_dir}/memories-organize.sh" --quiet

memory_path="$(resolve_memory "$memory_id")"
printf '%s\n' "$memory_path"
