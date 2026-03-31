#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/memories-common.sh"

ensure_memories_layout

printf 'initialized %s\n' "$(memories_dir)"
