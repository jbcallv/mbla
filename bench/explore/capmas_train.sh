#!/bin/bash
# retrain CAPMAS (bge-large, Qwen3-Embedding-0.6B) x 3 seeds on one GPU, one after another
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=${GPU:-0} HF_HOME=/scratch/jbcall/huggingface XDG_CACHE_HOME=/scratch/jbcall/.cache TMPDIR=/scratch/jbcall/tmp HF_HUB_OFFLINE=1
for encoder in bge-large qwen3-embedding-0.6b; do
  for seed in 0 1 2; do
    log=results/logs/capmas_train/$encoder-s$seed.log
    [ -s "$log" ] && grep -q "Early stopping\|Epoch 15/15" "$log" && continue
    .venv-train/bin/python -m mbla_bench.capmas_train --encoder $encoder --seed $seed > "$log" 2>&1 || echo "failed $encoder s$seed" >> results/logs/capmas_train/failures.txt
  done
done
echo done > results/logs/capmas_train/finished
