#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/memories-common.sh"

quiet=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet)
      quiet=1
      shift
      ;;
    *)
      printf 'usage: memories-organize.sh [--quiet]\n' >&2
      exit 1
      ;;
  esac
done

ensure_memories_layout

rm -rf "$(index_root)"
mkdir -p "$(index_root)/by-tag" "$(index_root)/by-path"

rows_file="$(mktemp)"
memory_count=0

while IFS= read -r file_path; do
  status_name="$(normalize_status "$(read_meta status "$file_path" || true)")"
  memory_id="$(read_meta id "$file_path" || true)"
  title="$(read_meta title "$file_path" || true)"
  updated_at="$(read_meta updated_at "$file_path" || true)"
  tags_csv="$(normalize_tags "$(read_meta tags "$file_path" || true)")"
  paths_csv="$(normalize_paths "$(read_meta paths "$file_path" || true)")"

  if [[ -z "$memory_id" ]]; then
    memory_id="$(basename "$file_path" .md)"
    set_meta id "$memory_id" "$file_path"
  fi

  if [[ -z "$updated_at" ]]; then
    updated_at="$(now_utc)"
    set_meta updated_at "$updated_at" "$file_path"
  fi

  target_path="$(memory_target_path "$status_name" "$memory_id")"
  if [[ "$file_path" != "$target_path" ]]; then
    mv "$file_path" "$target_path"
    file_path="$target_path"
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$updated_at" \
    "$status_name" \
    "$memory_id" \
    "$title" \
    "$tags_csv" \
    "$paths_csv" \
    "$file_path" >>"$rows_file"

  if [[ -n "$tags_csv" ]]; then
    IFS=',' read -r -a tags_array <<<"$tags_csv"
    for tag_value in "${tags_array[@]}"; do
      if [[ -z "$tag_value" ]]; then
        continue
      fi

      tag_dir="$(index_root)/by-tag/$(slugify "$tag_value")"
      mkdir -p "$tag_dir"
      ln -sf "$file_path" "${tag_dir}/$(basename "$file_path")"
    done
  fi

  if [[ -n "$paths_csv" ]]; then
    IFS=',' read -r -a paths_array <<<"$paths_csv"
    for path_value in "${paths_array[@]}"; do
      if [[ -z "$path_value" ]]; then
        continue
      fi

      path_dir="$(index_root)/by-path/$(slugify "$path_value")"
      mkdir -p "$path_dir"
      ln -sf "$file_path" "${path_dir}/$(basename "$file_path")"
    done
  fi

  memory_count=$((memory_count + 1))
done < <(collect_memory_files)

{
  printf 'updated_at\tstatus\tid\ttitle\ttags\tpaths\tfile\n'
  if [[ -s "$rows_file" ]]; then
    sort -r "$rows_file"
  fi
} >"$(index_root)/recent.tsv"

rm -f "$rows_file"

if [[ "$quiet" -ne 1 ]]; then
  printf 'organized %s memories under %s\n' "$memory_count" "$(memories_dir)"
fi
