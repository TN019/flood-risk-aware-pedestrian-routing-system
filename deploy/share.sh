#!/bin/sh
# Share this copy of the app through a temporary public link: builds the latest web client, starts
# the API and opens a Cloudflare tunnel (deploy/tunnel.py). Ctrl+C stops it.
set -e
cd "$(dirname "$0")/.."
if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv not found. Install it from https://docs.astral.sh/uv/" >&2
  exit 1
fi
exec uv run --project backend python deploy/tunnel.py "$@"
