#!/bin/bash
# after gpu1_queue.sh: re-run the scorers whose server failed to start before the import fix (2026-11-09)
cd "$(dirname "$0")/.."
exec >> results/logs/gpu1_queue.log 2>&1
until grep -q "^all done" results/logs/gpu1_queue.log; do sleep 60; done
SCORERS=capmas,capmas-scores,qwen3-reranker-0.6b,qwen3-reranker-8b
.venv/bin/python -m mbla_bench.orchestrate --experiments latency --methods "$SCORERS" --gpus 1
echo "latency retry exit $?"
.venv/bin/python -m mbla_bench.orchestrate --experiments fortis1,fortis2 --methods "$SCORERS" --gpus 1
echo "fortis retry exit $?"
.venv/bin/python -m mbla_bench.report latency > results/logs/report_latency.log 2>&1
.venv/bin/python -m mbla_bench.fortis report fortis1 data/external/fortis/task1.jsonl
.venv/bin/python -m mbla_bench.fortis report fortis2 data/external/fortis/task2.jsonl
echo "retry all done"
