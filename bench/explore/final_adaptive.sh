#!/bin/bash
# attack (c) on the final test set, run once with the settings fixed on development (D-62); Joseph's go 2026-11-10.
# card 1 after gpt-oss-120b; the deployed copy is stopped at the end so nothing is left on the card.
cd "$(dirname "$0")/.."
exec >> results/logs/final_adaptive.log 2>&1
until grep -q "^gpt-oss-120b exit" results/logs/pair_chain.log; do sleep 60; done
export CUDA_VISIBLE_DEVICES=1 HF_HOME=/scratch/jbcall/huggingface HF_HUB_OFFLINE=1 PATH=/usr/local/go/bin:$PATH
GPU=1 setsid bash explore/serve_attack_target.sh > results/logs/attack_target_server.log 2>&1 &
server=$!
trap 'kill -- -$server 2>/dev/null' EXIT
until curl -s localhost:8402/health > /dev/null; do kill -0 $server || { echo "server exit 1"; exit 1; }; sleep 10; done
.venv-train/bin/python -m mbla_bench.adaptive --items data/tasks/test.jsonl --out data/attacks/test_adaptive_qwen3-4b.jsonl --endpoint http://127.0.0.1:8402/v1 > results/logs/adaptive_final.log 2>&1 || { echo "search exit 1"; exit 1; }
mkdir -p results/raw/final-adaptive
for s in 0 1 2; do
  ../mbla/bin/mbla bench -items data/attacks/test_adaptive_qwen3-4b.jsonl -out results/raw/final-adaptive/qwen3-4b__full__s$s.jsonl -method qwen3-4b -scorer chat -input full -seed $s -initial 0.8 -admit 0.2 -hardware "shared GPU (other users' jobs present): latency not used, see the latency experiment" -warmup 5 -endpoint http://127.0.0.1:8402/v1 -model Qwen/Qwen3-4B -extra '{"chat_template_kwargs": {"enable_thinking": false}}' > /dev/null || echo "score s$s exit 1"
done
.venv/bin/python -m mbla_bench.report final-adaptive > results/logs/report_final-adaptive.log 2>&1
.venv/bin/python -m mbla_bench.adaptive report final-adaptive final data/attacks/test_adaptive_qwen3-4b.jsonl data/tasks/test.jsonl qwen3-4b
echo "final adaptive done"
