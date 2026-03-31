#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command_name="${1:-}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "$command_name" in
  init)
    exec "${script_dir}/memories-init.sh" "$@"
    ;;
  list)
    exec "${script_dir}/memories-list.sh" "$@"
    ;;
  new | create)
    exec "${script_dir}/memories-new.sh" "$@"
    ;;
  update | edit)
    exec "${script_dir}/memories-update.sh" "$@"
    ;;
  organize | reindex)
    exec "${script_dir}/memories-organize.sh" "$@"
    ;;
  *)
    printf 'usage: memories.sh <init|list|new|update|organize> [args...]\n' >&2
    exit 1
    ;;
esac
