#!/bin/bash
# deployed copy of the attacked helper for attack (c), same flags as config/models.yaml except port and memory share
cd "$(dirname "$0")/.."
export PATH=$PWD/.venv-serve/bin:$PATH CUDA_VISIBLE_DEVICES=${GPU:-0} HF_HOME=/scratch/jbcall/huggingface XDG_CACHE_HOME=/scratch/jbcall/.cache TMPDIR=/scratch/jbcall/tmp
MODEL=${MODEL:-Qwen/Qwen3-4B}; REVISION=${REVISION:-1cfa9a7208912126459214e8b04321603b3df60c}
exec vllm serve "$MODEL" --revision "$REVISION" --port ${PORT:-8402} --max-model-len 8192 --gpu-memory-utilization 0.35 --seed 0 --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}'
