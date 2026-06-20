#!/usr/bin/env bash
# Spin up each pattern/template one at a time and verify it responds.
# Each app gets its own PIXELTABLE_HOME (namespaces like "pipeline" differ across projects).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT_BASE=18100
RESULTS=()
PID=""

cleanup_server() {
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
  PID=""
}
trap cleanup_server EXIT

stop_postgres() {
  cleanup_server
  pkill -f pixeltable_pgserver 2>/dev/null || true
  pkill -f "pginstall/bin/postgres" 2>/dev/null || true
  # Kill stray template servers that bind default port 8000
  lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
  sleep 3
}

wait_for_url() {
  local url=$1
  local tries=${2:-120}
  for _ in $(seq 1 "$tries"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

check_http() {
  local name=$1
  local dir=$2
  local port=$3
  local start_cmd=$4
  local url=$5
  local home="/tmp/pxt-app-verify-${name}"

  echo ""
  echo "=== $name (port $port) ==="
  stop_postgres
  rm -rf "$home"

  (
    cd "$dir"
    export PIXELTABLE_HOME="$home"
    export PORT="$port"
    eval "$start_cmd"
  ) >"/tmp/pxt-app-verify-${name}.log" 2>&1 &
  PID=$!

  if wait_for_url "$url" 180; then
    echo "OK  $name -> $url"
    RESULTS+=("OK  $name")
  else
    echo "FAIL $name (no response at $url)"
    tail -25 "/tmp/pxt-app-verify-${name}.log" || true
    RESULTS+=("FAIL $name")
  fi
  stop_postgres
}

stop_postgres
echo "Starting one-by-one app verification..."

check_http "backend" "$ROOT/backend" "$PORT_BASE" \
  "uv run uvicorn main:app --host 127.0.0.1 --port $PORT_BASE" \
  "http://127.0.0.1:$PORT_BASE/api/health"

check_http "serving" "$ROOT/serving" "$((PORT_BASE + 1))" \
  "uv run pxt serve pipeline --port $((PORT_BASE + 1))" \
  "http://127.0.0.1:$((PORT_BASE + 1))/openapi.json"

check_http "knowledge-base" "$ROOT/templates/knowledge-base" "$((PORT_BASE + 2))" \
  "uv run uvicorn app:app --host 127.0.0.1 --port $((PORT_BASE + 2))" \
  "http://127.0.0.1:$((PORT_BASE + 2))/openapi.json"

check_http "chat-agent" "$ROOT/templates/chat-agent" "$((PORT_BASE + 3))" \
  "uv run uvicorn app:app --host 127.0.0.1 --port $((PORT_BASE + 3))" \
  "http://127.0.0.1:$((PORT_BASE + 3))/openapi.json"

check_http "audio-transcription" "$ROOT/templates/audio-transcription" "$((PORT_BASE + 4))" \
  "uv run uvicorn app:app --host 127.0.0.1 --port $((PORT_BASE + 4))" \
  "http://127.0.0.1:$((PORT_BASE + 4))/openapi.json"

check_http "full-stack-showcase" "$ROOT/templates/full-stack-showcase" "$((PORT_BASE + 5))" \
  "uv run uvicorn app:app --host 127.0.0.1 --port $((PORT_BASE + 5))" \
  "http://127.0.0.1:$((PORT_BASE + 5))/api/health"

check_http "video-search" "$ROOT/templates/video-search" "$((PORT_BASE + 6))" \
  "uv run pxt serve videointel --port $((PORT_BASE + 6))" \
  "http://127.0.0.1:$((PORT_BASE + 6))/openapi.json"

check_http "media-indexing" "$ROOT/templates/media-indexing" "$((PORT_BASE + 7))" \
  "uv run pxt serve pipeline --port $((PORT_BASE + 7))" \
  "http://127.0.0.1:$((PORT_BASE + 7))/openapi.json"

check_http "image-dataset" "$ROOT/templates/image-dataset" "$((PORT_BASE + 8))" \
  "uv run pxt serve datalab --port $((PORT_BASE + 8))" \
  "http://127.0.0.1:$((PORT_BASE + 8))/openapi.json"

echo ""
echo "=== batch (pipeline.py) ==="
stop_postgres
BATCH_HOME="/tmp/pxt-app-verify-batch"
rm -rf "$BATCH_HOME"
if (
  cd "$ROOT/batch"
  export PIXELTABLE_HOME="$BATCH_HOME"
  export SERVING_DB_URL="sqlite:///${BATCH_HOME}/serving.db"
  uv run python pipeline.py
) >"/tmp/pxt-app-verify-batch.log" 2>&1; then
  echo "OK  batch pipeline"
  RESULTS+=("OK  batch")
else
  echo "FAIL batch pipeline"
  tail -20 "/tmp/pxt-app-verify-batch.log" || true
  RESULTS+=("FAIL batch")
fi
stop_postgres

echo ""
echo "========== SUMMARY =========="
printf '%s\n' "${RESULTS[@]}"

if printf '%s\n' "${RESULTS[@]}" | grep -q '^FAIL'; then
  exit 1
fi
