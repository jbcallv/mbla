#!/usr/bin/env bash
# long-running helper server for the enforcement side to call over the network.
# waits for a gpu with enough free memory (or uses $GPU), then serves on 0.0.0.0:$PORT with the api key from $KEY_FILE.
# MODEL is a hub id (pinned by REVISION) or a local folder (REVISION empty); SERVED lists the names clients may use.
set -euo pipefail

PORT=${PORT:-8300}
KEY_FILE=${KEY_FILE:-/scratch/jbcall/boundclaw/.secrets/mbla_api_key}
MODEL=${MODEL:-Qwen/Qwen3-8B}
REVISION=${REVISION-b968826d9c46dd6066d109eabc6255188de91218}
SERVED=${SERVED:-Qwen/Qwen3-8B}
MEMORY_FRACTION=${MEMORY_FRACTION:-0.55}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-8192}
HERE=$(cd "$(dirname "$0")/.." && pwd)

needed_mib() {
  awk -v fraction="$MEMORY_FRACTION" 'BEGIN {print int(fraction * 45458) + 512}'
}

gpu_with_room() {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | sort -t, -k2 -nr | awk -F', ' -v need="$(needed_mib)" '$2 >= need {print $1; exit}'
}

until [ -n "${GPU:-}" ]; do
  GPU=$(gpu_with_room) || true
  [ -n "$GPU" ] || sleep 30
done
echo "starting $MODEL@$REVISION on gpu $GPU at $(date -u +%FT%TZ)"

export PATH="$HERE/.venv-serve/bin:$PATH" CUDA_VISIBLE_DEVICES="$GPU"
export HF_HOME=/scratch/jbcall/huggingface XDG_CACHE_HOME=/scratch/jbcall/.cache TMPDIR=/scratch/jbcall/tmp
exec vllm serve "$MODEL" ${REVISION:+--revision "$REVISION"} --served-model-name $SERVED \
  --host 0.0.0.0 --port "$PORT" --api-key "$(cat "$KEY_FILE")" \
  --max-model-len "$MAX_MODEL_LEN" --gpu-memory-utilization "$MEMORY_FRACTION" --seed 0 \
  --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}'
