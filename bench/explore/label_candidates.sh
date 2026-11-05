#!/bin/bash
# each second-reader candidate labels the pilot and review rows with the frozen prompt, on gpu 1 (D-41).
source .venv/bin/activate
export GPU=1
port=8160
for pair in "$@"; do
  name=${pair%%=*}; model=${pair#*=}
  revision=$(ls /scratch/jbcall/huggingface/hub/models--${model//\//--}/snapshots | head -1)
  explore/serve_judge.sh $model $revision $port 5000 1 > results/logs/serve_label_$name.log 2>&1 & server=$!
  until curl -s -m 3 localhost:$port/v1/models > /dev/null || ! kill -0 $server 2>/dev/null; do timeout 5 tail -f /dev/null; done
  python -m mbla_bench.label_judge --endpoint http://127.0.0.1:$port/v1 --model $model --out data/review/sample/judge_$name.csv 2>&1 | tail -1 | cut -c1-140
  kill $server; wait $server 2>/dev/null; timeout 20 tail -f /dev/null
  python -m mbla_bench.label_alignment --judge data/review/sample/judge_$name.csv --pilot-only 2>&1 | tail -3 | cut -c1-160
  port=$((port + 1))
done
