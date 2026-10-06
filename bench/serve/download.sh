#!/usr/bin/env bash
# downloads every local model at its pinned revision into HF_HOME (on scratch; the home disk is full)
set -euo pipefail
export HF_HOME=${HF_HOME:-/scratch/jbcall/huggingface}
export HF_HUB_ENABLE_HF_TRANSFER=0

fetch() {
  local repo=$1 revision=$2
  .venv-serve/bin/hf download "$repo" --revision "$revision" --quiet > /dev/null
  echo "ok $repo@$revision"
}

fetch Qwen/Qwen3-0.6B c1899de289
fetch Qwen/Qwen3-1.7B 70d244cc86
fetch Qwen/Qwen3-4B 1cfa9a7208
fetch Qwen/Qwen3-8B b968826d9c
fetch Qwen/Qwen3-32B-AWQ 0499c3ac83
fetch microsoft/Phi-4-mini-instruct cfbefacb99
fetch openai/gpt-oss-20b 6cee5e81ee
fetch openai/gpt-oss-120b b5c939de8f
fetch Qwen/Qwen3-Reranker-0.6B e61197ed45
fetch Qwen/Qwen3-Reranker-4B 22e683669b
fetch Qwen/Qwen3-Reranker-8B 77d193c791
fetch Contrastive-LM/CLM-v0.1-8B e939398d45
fetch convaiinnovations/laya 55cf4c4ebb
fetch Qwen/Qwen3-30B-A3B ad44e777bcd18fa416d9da3bd8f70d33ebb85d39
fetch casperhansen/llama-3.3-70b-instruct-awq 64d255621f40b42adaf6d1f32a47e1d4534c0f14
