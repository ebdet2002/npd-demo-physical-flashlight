#!/usr/bin/env bash
# Spin up the CAD + PCB browser viewers.
#
# Serves the repo root with a plain static file server (the viewers fetch
# files from cad/ and pcb/, so the root — not viewers/ — must be served),
# then opens both viewers in the default browser.
#
# Usage: ./start.sh [port]        (default port: 8080, or $PORT)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-${PORT:-8080}}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 not found — it's needed to run the static file server." >&2
  exit 1
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "error: port $PORT is already in use. Try: ./start.sh $((PORT + 1))" >&2
  exit 1
fi

CAD_URL="http://localhost:$PORT/viewers/cad-viewer/"
PCB_URL="http://localhost:$PORT/viewers/pcb-viewer/"

open_url() {
  if command -v open >/dev/null 2>&1; then
    open "$1"                       # macOS
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" >/dev/null 2>&1   # Linux
  fi
}

cd "$ROOT"
python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT INT TERM

# Wait (up to ~10s) for the server to accept connections before opening tabs.
for _ in $(seq 1 100); do
  if curl -fs -o /dev/null "http://127.0.0.1:$PORT/"; then break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "error: file server failed to start on port $PORT." >&2
    exit 1
  fi
  sleep 0.1
done

echo "Serving $ROOT on http://localhost:$PORT"
echo "  CAD viewer: $CAD_URL"
echo "  PCB viewer: $PCB_URL"
echo "Press Ctrl+C to stop."

open_url "$CAD_URL"
open_url "$PCB_URL"

wait "$SERVER_PID"
