#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/memories-common.sh"

status_filter=""
tag_filter=""
path_filter=""
query_filter=""
limit_value=50
long_output=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --status)
      status_filter="$(normalize_status "${2:-}")"
      shift 2
      ;;
    --tag)
      tag_filter="$(normalize_tags "${2:-}")"
      shift 2
      ;;
    --path)
      path_filter="$(normalize_paths "${2:-}")"
      shift 2
      ;;
    --query)
      query_filter="${2:-}"
      shift 2
      ;;
    --limit)
      limit_value="${2:-50}"
      shift 2
      ;;
    --long)
      long_output=1
      shift
      ;;
    *)
      printf 'usage: memories-list.sh [--status inbox|active|archive] [--tag name] [--path repo/file] [--query text] [--limit n] [--long]\n' >&2
      exit 1
      ;;
  esac
done

ensure_memories_layout

if [[ ! -f "$(index_root)/recent.tsv" ]]; then
  "${script_dir}/memories-organize.sh" --quiet
fi

match_count=0

while IFS=$'\t' read -r updated_at status_name memory_id title tags_csv paths_csv file_path; do
  if [[ "$updated_at" == "updated_at" ]]; then
    continue
  fi

  if [[ -n "$status_filter" && "$status_name" != "$status_filter" ]]; then
    continue
  fi

  if [[ -n "$tag_filter" ]] && ! csv_has_value "$tags_csv" "$tag_filter"; then
    continue
  fi

  if [[ -n "$path_filter" ]] && ! csv_has_value "$paths_csv" "$path_filter"; then
    continue
  fi

  if [[ -n "$query_filter" ]]; then
    query_in_row=0
    if printf '%s\n%s\n%s\n%s\n%s\n' "$memory_id" "$title" "$tags_csv" "$paths_csv" "$status_name" | rg -qi --fixed-strings -- "$query_filter"; then
      query_in_row=1
    elif rg -qi --fixed-strings -- "$query_filter" "$file_path"; then
      query_in_row=1
    fi

    if [[ "$query_in_row" -ne 1 ]]; then
      continue
    fi
  fi

  if [[ "$long_output" -eq 1 ]]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$updated_at" \
      "$status_name" \
      "$memory_id" \
      "$title" \
      "$tags_csv" \
      "$paths_csv" \
      "$(relative_to_repo "$file_path")"
  else
    printf '%s\t%s\t%s\t%s\t%s\n' \
      "$updated_at" \
      "$status_name" \
      "$memory_id" \
      "$title" \
      "$tags_csv"
  fi

  match_count=$((match_count + 1))
  if [[ "$match_count" -ge "$limit_value" ]]; then
    break
  fi
done <"$(index_root)/recent.tsv"
