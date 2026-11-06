#!/bin/bash
# small models on one gpu each, then the 8B models across both: adam's state alone outgrows one gpu at 8B.
.venv-train/bin/python -m mbla_bench.train_all 0 Qwen/Qwen3-1.7B Qwen/Qwen3-4B &
.venv-train/bin/python -m mbla_bench.train_all 1 Qwen/Qwen3-Reranker-0.6B &
wait
.venv-train/bin/python -m mbla_bench.train_all 0+1 Qwen/Qwen3-8B Qwen/Qwen3-Reranker-8B
