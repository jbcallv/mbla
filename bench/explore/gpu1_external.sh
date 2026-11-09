#!/bin/bash
# after gpu1_retry.sh: mostargate for the prompted model helpers and the fifteen fine-tuned helpers (2026-11-09)
cd "$(dirname "$0")/.."
exec >> results/logs/gpu1_queue.log 2>&1
export PATH=/usr/local/go/bin:$PATH
until grep -q "^retry all done" results/logs/gpu1_queue.log; do sleep 60; done
.venv/bin/python -m mbla_bench.orchestrate --experiments mostargate --methods capmas,capmas-scores,qwen3-reranker-0.6b,qwen3-reranker-8b,qwen3-1.7b,qwen3-4b,qwen3-8b --gpus 1
echo "mostargate prompted exit $?"
TUNED=$(for m in qwen3-1.7b qwen3-4b qwen3-8b qwen3-reranker-0.6b qwen3-reranker-8b; do for s in 0 1 2; do printf "%s-tuned-s%s," $m $s; done; done)
.venv/bin/python -m mbla_bench.orchestrate --experiments mostargate --methods "${TUNED%,}" --gpus 1
echo "mostargate tuned exit $?"
.venv/bin/python -m mbla_bench.mostargate report mostargate
echo "external all done"
