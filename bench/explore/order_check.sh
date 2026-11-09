#!/bin/bash
# D-64 on card 1 after the external queue: fine-tuned Qwen3-4B seed 2, deployed vs trained answer order, development only
cd "$(dirname "$0")/.."
exec >> results/logs/order_check.log 2>&1
until grep -q "^external all done" results/logs/gpu1_queue.log; do sleep 60; done
export PATH=$PWD/.venv-serve/bin:$PATH CUDA_VISIBLE_DEVICES=1 HF_HOME=/scratch/jbcall/huggingface XDG_CACHE_HOME=/scratch/jbcall/.cache TMPDIR=/scratch/jbcall/tmp
MODEL=/scratch/jbcall/boundclaw/bench/models/Qwen3-4B/lr2e-05-seed2
vllm serve $MODEL --port 8406 --max-model-len 8192 --gpu-memory-utilization 0.85 --seed 0 --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}' > results/logs/order_check_server.log 2>&1 &
server=$!
until curl -s localhost:8406/health > /dev/null; do sleep 10; done
.venv/bin/python -m mbla_bench.order_check --endpoint http://127.0.0.1:8406/v1 --served $MODEL
kill $server
.venv/bin/python -m mbla_bench.report dev-order
echo "order check done"
