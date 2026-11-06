#!/bin/bash
# remaining prompted development runs, then the two 8B models across both gpus
cd "$(dirname "$0")/.."
timeout 14400 .venv/bin/python -m mbla_bench.orchestrate --experiments dev --methods qwen3-30b,gpt-oss-120b --gpus 0,1
.venv-train/bin/python -m mbla_bench.train_all 0+1 Qwen/Qwen3-8B Qwen/Qwen3-Reranker-8B
