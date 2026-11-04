#!/bin/bash
# Starts the web app on http://localhost:5173. Calls to /api go to the backend on :8000.
set -e
cd "$(dirname "$0")"
export PATH="$(pwd)/.tools/node/bin:$PATH"
export npm_config_cache="$(pwd)/.tools/npm-cache"
export npm_config_update_notifier=false
[ -d node_modules ] || { echo "Run ./setup.sh first."; exit 1; }
exec npm run dev -- --open
