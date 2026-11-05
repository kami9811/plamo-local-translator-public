#!/usr/bin/env bash
set -euo pipefail
PLAMO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$PLAMO_ROOT/.runtime/node/bin:$PATH"
export npm_config_cache="$PLAMO_ROOT/.runtime/npm-cache"
exec "$@"
