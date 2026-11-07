#!/bin/bash
# one more try at the two-gpu prompted helpers (D-57); stray servers are stopped afterwards
cd "$(dirname "$0")/.."
export NCCL_P2P_DISABLE=1 VLLM_ENGINE_READY_TIMEOUT_S=1800
timeout 10800 .venv/bin/python -m mbla_bench.orchestrate --experiments dev --methods qwen3-30b,gpt-oss-120b --gpus 0,1
echo "exit $?"
pgrep -u jbcall -f "vllm serve|VLLM::" | xargs -r kill
sleep 10
pgrep -u jbcall -f "vllm serve|VLLM::" | xargs -r kill -9
