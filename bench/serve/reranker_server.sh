#!/usr/bin/env bash
# long-running reranker helper for the enforcement side, behind the /score api (bench/serve/decision_server.py).
# waits for a gpu with enough free memory (or uses $GPU), then serves on 0.0.0.0:$PORT with the api key from $KEY_FILE.
set -euo pipefail

PORT=${PORT:-8300}
KEY_FILE=${KEY_FILE:-/scratch/jbcall/boundclaw/.secrets/mbla_api_key}
MODEL=${MODEL:-/scratch/jbcall/boundclaw/bench/models/Qwen3-Reranker-8B/chosen-seed1}
NEEDED_MIB=${NEEDED_MIB:-22000}
HERE=$(cd "$(dirname "$0")/.." && pwd)

gpu_with_room() {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | sort -t, -k2 -nr | awk -F', ' -v need="$NEEDED_MIB" '$2 >= need {print $1; exit}'
}

until [ -n "${GPU:-}" ]; do
  GPU=$(gpu_with_room) || true
  [ -n "$GPU" ] || sleep 60
done
echo "starting $MODEL on gpu $GPU at $(date -u +%FT%TZ)"

export CUDA_VISIBLE_DEVICES="$GPU"
export HF_HOME=/scratch/jbcall/huggingface XDG_CACHE_HOME=/scratch/jbcall/.cache TMPDIR=/scratch/jbcall/tmp
cd "$HERE"
exec .venv-serve/bin/python serve/decision_server.py --backend qwen3-reranker --model "$MODEL" \
  --host 0.0.0.0 --port "$PORT" --api-key-file "$KEY_FILE"
