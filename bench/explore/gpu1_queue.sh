#!/bin/bash
# card 1 queue (2026-11-09): latency (RQ4), then FORTIS 1-2 for the prompted helpers. qwen3-30b and gpt-oss-120b need two working GPUs (D-55 to D-57)
set -x
cd "$(dirname "$0")/.."
exec > >(tee -a results/logs/gpu1_queue.log) 2>&1
export PATH=/usr/local/go/bin:$PATH
ONE_GPU=capmas,capmas-scores,qwen3-reranker-0.6b,qwen3-reranker-8b,qwen3-1.7b,qwen3-4b,qwen3-8b
make mbla verify || exit 1
.venv/bin/python -m mbla_bench.orchestrate --experiments latency --methods "$ONE_GPU" --gpus 1
echo "latency exit $?"
make fortis-data || exit 1
.venv/bin/python -m mbla_bench.orchestrate --experiments fortis1,fortis2 --methods "set-only,manifest-only,lexical,random-25,random-50,random-75,$ONE_GPU" --gpus 1
echo "fortis exit $?"
.venv/bin/python -m mbla_bench.report latency > results/logs/report_latency.log 2>&1
.venv/bin/python -m mbla_bench.fortis report fortis1 data/external/fortis/task1.jsonl
.venv/bin/python -m mbla_bench.fortis report fortis2 data/external/fortis/task2.jsonl
echo "all done"
