#!/usr/bin/env bash
set -euo pipefail

readonly MEMORIES_STATUSES="inbox active archive"

skill_dir() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
}

repo_root() {
  git rev-parse --show-toplevel 2>/dev/null
}

require_repo() {
  if ! repo_root >/dev/null; then
    printf 'memories: run this inside a git repository\n' >&2
    return 1
  fi
}

memories_dir() {
  printf '%s/.memories\n' "$(repo_root)"
}

entries_root() {
  printf '%s/entries\n' "$(memories_dir)"
}

status_dir() {
  printf '%s/%s\n' "$(entries_root)" "$1"
}

index_root() {
  printf '%s/index\n' "$(memories_dir)"
}

normalize_status() {
  case "${1:-inbox}" in
    inbox | active | archive) printf '%s\n' "$1" ;;
    *) printf 'inbox\n' ;;
  esac
}

now_utc() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

timestamp_id() {
  date -u '+%Y%m%d%H%M%S'
}

slugify() {
  printf '%s' "${1:-}" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-{2,}/-/g'
}

safe_slug() {
  local normalized_slug

  normalized_slug="$(slugify "${1:-}")"
  if [[ -z "$normalized_slug" ]]; then
    printf 'memory\n'
  else
    printf '%s\n' "$normalized_slug"
  fi
}

normalize_csv() {
  printf '%s' "${1:-}" \
    | tr ';' ',' \
    | tr '\n' ',' \
    | sed -E 's/[[:space:]]*,[[:space:]]*/,/g; s/^[[:space:],]+//; s/[[:space:],]+$//'
}

sort_csv_unique() {
  local normalized_csv="$1"

  if [[ -z "$normalized_csv" ]]; then
    return 0
  fi

  printf '%s' "$normalized_csv" \
    | tr ',' '\n' \
    | sed -E '/^[[:space:]]*$/d; s/^[[:space:]]+//; s/[[:space:]]+$//' \
    | sort -u \
    | paste -sd ',' -
}

normalize_tags() {
  local normalized_tags

  normalized_tags="$(normalize_csv "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')")"
  sort_csv_unique "$normalized_tags"
}

normalize_paths() {
  sort_csv_unique "$(normalize_csv "${1:-}")"
}

merge_csv() {
  local left_csv="${1:-}"
  local right_csv="${2:-}"
  local merged_csv

  merged_csv="$(normalize_csv "${left_csv},${right_csv}")"
  sort_csv_unique "$merged_csv"
}

csv_has_value() {
  local csv_values="$1"
  local expected_value="$2"
  local current_value

  IFS=',' read -r -a current_values <<<"$csv_values"
  for current_value in "${current_values[@]}"; do
    if [[ "$current_value" == "$expected_value" ]]; then
      return 0
    fi
  done
  return 1
}

copy_memory_gitignore() {
  local source_file
  local target_file

  source_file="$(skill_dir)/assets/repo-local/.gitignore"
  target_file="$(memories_dir)/.gitignore"

  if [[ ! -f "$target_file" ]]; then
    cp "$source_file" "$target_file"
  fi
}

ensure_git_exclude() {
  local git_dir
  local exclude_file
  local needle

  git_dir="$(git rev-parse --git-dir)"
  exclude_file="${git_dir}/info/exclude"
  needle='/.memories/'

  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"

  if ! grep -Fqx "$needle" "$exclude_file"; then
    printf '\n%s\n' "$needle" >>"$exclude_file"
  fi
}

ensure_memories_layout() {
  require_repo
  mkdir -p \
    "$(status_dir inbox)" \
    "$(status_dir active)" \
    "$(status_dir archive)" \
    "$(index_root)/by-tag" \
    "$(index_root)/by-path"
  copy_memory_gitignore
  ensure_git_exclude
}

relative_to_repo() {
  local absolute_path="$1"
  local root_dir

  root_dir="$(repo_root)"
  printf '%s\n' "${absolute_path#"${root_dir}/"}"
}

collect_memory_files() {
  find "$(entries_root)" -type f -name '*.md' | sort
}

read_meta() {
  local key="$1"
  local file_path="$2"

  awk -v key="$key" '
    NR == 1 && $0 == "---" {
      in_header = 1
      next
    }
    in_header && $0 == "---" {
      exit
    }
    in_header && $0 ~ ("^" key ":") {
      sub("^" key ":[[:space:]]*", "", $0)
      print
      exit
    }
  ' "$file_path"
}

set_meta() {
  local key="$1"
  local value="$2"
  local file_path="$3"
  local temp_file

  temp_file="$(mktemp)"

  awk -v key="$key" -v value="$value" '
    NR == 1 && $0 == "---" {
      in_header = 1
      print
      next
    }
    in_header && $0 == "---" {
      if (!updated) {
        print key ": " value
      }
      in_header = 0
      print
      next
    }
    in_header && $0 ~ ("^" key ":") {
      print key ": " value
      updated = 1
      next
    }
    {
      print
    }
  ' "$file_path" >"$temp_file"

  mv "$temp_file" "$file_path"
}

memory_target_path() {
  local status_name="$1"
  local memory_id="$2"

  printf '%s/%s.md\n' "$(status_dir "$status_name")" "$memory_id"
}

canonicalize_path() {
  local input_path="$1"
  local parent_dir
  local file_name

  if [[ ! -e "$input_path" ]]; then
    return 1
  fi

  parent_dir="$(cd "$(dirname "$input_path")" && pwd -P)"
  file_name="$(basename "$input_path")"
  printf '%s/%s\n' "$parent_dir" "$file_name"
}

is_memory_file_path() {
  local input_path="$1"
  local absolute_path
  local entries_dir

  absolute_path="$(canonicalize_path "$input_path")" || return 1
  entries_dir="$(entries_root)"

  if [[ ! -f "$absolute_path" ]]; then
    return 1
  fi

  case "$absolute_path" in
    "${entries_dir}"/*/*.md) return 0 ;;
    *) return 1 ;;
  esac
}

ensure_unique_memory_id() {
  local status_name="$1"
  local base_id="$2"
  local candidate_id="$base_id"
  local candidate_path
  local suffix_idx=2

  candidate_path="$(memory_target_path "$status_name" "$candidate_id")"
  while [[ -e "$candidate_path" ]]; do
    candidate_id="${base_id}-${suffix_idx}"
    candidate_path="$(memory_target_path "$status_name" "$candidate_id")"
    suffix_idx=$((suffix_idx + 1))
  done

  printf '%s\n' "$candidate_id"
}

resolve_memory() {
  local selector="$1"
  local file_path
  local match_count=0
  local matched_path=""

  if [[ -f "$selector" ]]; then
    if is_memory_file_path "$selector"; then
      canonicalize_path "$selector"
      return 0
    fi

    printf 'memories: selector is not a memory file: %s\n' "$selector" >&2
    return 1
  fi

  while IFS= read -r file_path; do
    local base_name
    local memory_id
    local memory_slug

    base_name="$(basename "$file_path" .md)"
    memory_id="$(read_meta id "$file_path" || true)"
    memory_slug="$(read_meta slug "$file_path" || true)"

    if [[ "$selector" == "$base_name" || "$selector" == "$memory_id" || "$selector" == "$memory_slug" ]]; then
      matched_path="$file_path"
      match_count=$((match_count + 1))
    fi
  done < <(collect_memory_files)

  if [[ "$match_count" -eq 1 ]]; then
    printf '%s\n' "$matched_path"
    return 0
  fi

  if [[ "$match_count" -gt 1 ]]; then
    printf 'memories: selector matched multiple memories: %s\n' "$selector" >&2
  else
    printf 'memories: memory not found: %s\n' "$selector" >&2
  fi

  return 1
}
