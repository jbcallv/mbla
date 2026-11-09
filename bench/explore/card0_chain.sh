#!/bin/bash
# card 0 (2026-11-09): wait for the development attack search, then Qwen3-Embedding CAPMAS training, then retrained CAPMAS evaluation
cd "$(dirname "$0")/.."
until [ "$(wc -l < data/attacks/dev_adaptive_qwen3-4b.log.jsonl 2>/dev/null || echo 0)" -ge 172 ]; do sleep 60; done
sleep 30
GPU=0 explore/capmas_train.sh >> results/logs/capmas_train/queue.log 2>&1
GPU=0 explore/capmas_after.sh
