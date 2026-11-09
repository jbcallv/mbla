#!/bin/bash
# development run 3 of attack (c), after card 0's CAPMAS training; then scored by the benchmark (D-62)
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=0 HF_HOME=/scratch/jbcall/huggingface HF_HUB_OFFLINE=1
until [ -e results/logs/capmas_train/finished ]; do sleep 60; done
.venv-train/bin/python -m mbla_bench.adaptive --endpoint http://127.0.0.1:8402/v1 --out data/attacks/dev_adaptive_qwen3-4b.jsonl > results/logs/adaptive_dev3.log 2>&1 || exit 1
mkdir -p results/raw/dev-adaptive
for s in 0 1 2; do
  ../mbla/bin/mbla bench -items data/attacks/dev_adaptive_qwen3-4b.jsonl -out results/raw/dev-adaptive/qwen3-4b__full__s$s.jsonl -method qwen3-4b -scorer chat -input full -seed $s -initial 0.8 -admit 0.2 -hardware "shared GPU (other users' jobs present): latency not used, see the latency experiment" -warmup 5 -endpoint http://127.0.0.1:8402/v1 -model Qwen/Qwen3-4B -extra '{"chat_template_kwargs": {"enable_thinking": false}}' > /dev/null 2>&1
done
.venv/bin/python -m mbla_bench.report dev-adaptive > results/logs/report_dev-adaptive.log 2>&1
.venv/bin/python -m mbla_bench.adaptive report dev-adaptive dev data/attacks/dev_adaptive_qwen3-4b.jsonl data/tasks/dev.jsonl qwen3-4b > results/logs/adaptive_dev3_budget.log
echo done >> results/logs/adaptive_dev3_budget.log
