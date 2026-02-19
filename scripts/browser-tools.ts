#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPL_PATH="${SCRIPT_DIR}/browser-tools.impl.ts"

if [ ! -f "$IMPL_PATH" ]; then
  echo "browser-tools: implementation not found at ${IMPL_PATH}" >&2
  exit 1
fi

CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles-browser-tools"
PKG_JSON="${CACHE_ROOT}/package.json"
NODE_MODULES="${CACHE_ROOT}/node_modules"
RUNTIME_IMPL="${CACHE_ROOT}/browser-tools.impl.ts"

mkdir -p "$CACHE_ROOT"

if [ ! -f "$PKG_JSON" ]; then
  cat > "$PKG_JSON" <<'PKG'
{
  "name": "dotfiles-browser-tools-runtime",
  "private": true,
  "version": "0.0.0"
}
PKG
fi

if [ ! -d "$NODE_MODULES/tsx" ] || [ ! -d "$NODE_MODULES/commander" ] || [ ! -d "$NODE_MODULES/puppeteer-core" ]; then
  npm install \
    --prefix "$CACHE_ROOT" \
    --silent \
    --no-fund \
    --no-audit \
    --save-exact \
    tsx commander puppeteer-core
fi

# Run a cached copy so Node module resolution starts from CACHE_ROOT, where
# dependencies are installed.
if [ ! -f "$RUNTIME_IMPL" ] || ! cmp -s "$IMPL_PATH" "$RUNTIME_IMPL"; then
  cp "$IMPL_PATH" "$RUNTIME_IMPL"
fi

exec node "$NODE_MODULES/tsx/dist/cli.mjs" "$RUNTIME_IMPL" "$@"
