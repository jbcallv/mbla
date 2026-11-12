#!/usr/bin/env bash
# prompted (not fine-tuned) qwen3-4b for boundclaw on the rented pod, with the benchmark's decoding settings.
# flashinfer sampler off: the pod has no cuda compiler for its kernel.
# python env on the pod's local disk (reinstalled after a restart), model and key on its permanent disk.
set -euo pipefail

V=/root/venv-vllm
export HF_HOME=/workspace/hf PIP_CACHE_DIR=/root/pipcache
[ -x $V/bin/vllm ] || { python3 -m venv $V && $V/bin/pip install -q vllm==0.30.0; }
VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_API_KEY=$(cat /workspace/mbla/api_key) setsid nohup $V/bin/vllm serve Qwen/Qwen3-4B \
  --revision 1cfa9a7208912126459214e8b04321603b3df60c \
  --served-model-name mbla-qwen3-4b Qwen/Qwen3-4B mbla-reranker-8b-tuned mbla-qwen3-4b-tuned Qwen/Qwen3-8B \
  --host 0.0.0.0 --port 8300 --max-model-len 8192 --gpu-memory-utilization 0.85 --seed 0 \
  --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}' \
  > /workspace/mbla/vllm.log 2>&1 < /dev/null &
