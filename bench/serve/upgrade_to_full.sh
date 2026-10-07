#!/usr/bin/env bash
# waits until a gpu has room for full-precision qwen3-8b, then replaces the 4-bit server on the same port.
# clients keep the same endpoint, key and model name; expect a minute or two of downtime while the full model loads.
set -euo pipefail

PORT=${PORT:-8300}
FULL_FRACTION=${FULL_FRACTION:-0.55}
HERE=$(cd "$(dirname "$0")" && pwd)
LOG_DIR=$(cd "$HERE/.." && pwd)/results/logs

needed_mib() {
  awk -v fraction="$FULL_FRACTION" 'BEGIN {print int(fraction * 45458) + 1024}'
}

room_for_full() {
  nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | awk -v need="$(needed_mib)" '$1 >= need {found=1} END {exit !found}'
}

quantized_server_pids() {
  pgrep -f "vllm serve Qwen/Qwen3-8B-AWQ" || true
}

until room_for_full; do
  sleep 60
done
echo "room for full model at $(date -u +%FT%TZ); stopping the 4-bit server"

for pid in $(quantized_server_pids); do
  kill -TERM -- "-$(ps -o pgid= -p "$pid" | tr -d ' ')" 2>/dev/null || true
done
while [ -n "$(quantized_server_pids)" ]; do
  sleep 2
done

MEMORY_FRACTION="$FULL_FRACTION" MAX_MODEL_LEN=8192 setsid nohup bash "$HERE/integration_server.sh" > "$LOG_DIR/integration_server.log" 2>&1 < /dev/null &
until curl -s -m 3 "http://127.0.0.1:$PORT/health" > /dev/null; do
  sleep 10
done
echo "full Qwen3-8B serving on port $PORT at $(date -u +%FT%TZ)"
