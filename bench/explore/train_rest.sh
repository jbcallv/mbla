#!/bin/bash
# small models on gpu 0, then the 8B models across both gpus: adam's state alone outgrows one gpu at 8B.
small=$1
.venv-train/bin/python -m mbla_bench.train_all 0 Qwen/Qwen3-1.7B Qwen/Qwen3-4B
while kill -0 $small 2>/dev/null; do timeout 30 tail -f /dev/null; done
.venv-train/bin/python -m mbla_bench.train_all 0+1 Qwen/Qwen3-8B Qwen/Qwen3-Reranker-8B
