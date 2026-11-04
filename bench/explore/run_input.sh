#!/bin/bash
# exploratory input comparison for one chat model on the development set. usage: explore/run_input.sh <method> <model> <revision> <port>
set -u
method=$1; model=$2; revision=$3; port=$4
out=results/explore/input
.venv/bin/python explore/input_variants.py $out
export PATH=$PWD/.venv-serve/bin:$PATH CUDA_VISIBLE_DEVICES=0 HF_HOME=/scratch/jbcall/huggingface XDG_CACHE_HOME=/scratch/jbcall/.cache TMPDIR=/scratch/jbcall/tmp
vllm serve $model --revision $revision --port $port --max-model-len 8192 --gpu-memory-utilization 0.85 --seed 0 \
  --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}' > results/logs/explore_$method.log 2>&1 &
server=$!
trap 'kill $server; sleep 5' EXIT
until curl -sf http://127.0.0.1:$port/health > /dev/null; do kill -0 $server || exit 1; sleep 5; done
bench() {
  name=$1; shift
  ../mbla/bin/mbla bench -out $out/${method}__$name.jsonl -method $method -scorer chat -seed 0 -initial 0.8 -admit 0.2 -hardware "1x NVIDIA L40S 46GB" -warmup 5 \
    -endpoint http://127.0.0.1:$port/v1 -model $model -extra '{"chat_template_kwargs": {"enable_thinking": false}}' "$@"
}
bench text -items data/tasks/dev.jsonl -input text
bench manifest -items data/tasks/dev.jsonl -input full
bench manifest_desc -items data/tasks/dev.jsonl -input full -glossary data/universe.json
bench manifest_op_receiver -items $out/dev_op_receiver.jsonl -input full
bench manifest_op_receiver_history -items $out/dev_op_receiver_history.jsonl -input full
bench manifest_desc_op_receiver -items $out/dev_op_receiver.jsonl -input full -glossary data/universe.json
