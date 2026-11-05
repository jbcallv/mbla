#!/bin/bash
# runs each judge candidate on the known-good and broken plans, one server at a time (D-40). usage: explore/bakeoff_judges.sh <name=model> ...
source .venv/bin/activate
mkdir -p data/synth/work/bakeoff
port=8130
for pair in "$@"; do
  name=${pair%%=*}; model=${pair#*=}
  dir=/scratch/jbcall/huggingface/hub/models--${model//\//--}/snapshots
  revision=$(ls $dir | head -1)
  echo "$name $model $revision"
  explore/serve_judge.sh $model $revision $port 1600 3 > results/logs/serve_$name.log 2>&1 &
  server=$!; echo $server > results/logs/judge.pid
  until curl -s -m 3 localhost:$port/v1/models > /dev/null || ! kill -0 $server 2>/dev/null; do timeout 5 tail -f /dev/null; done
  if kill -0 $server 2>/dev/null; then
    for set in good broken; do
      input=data/synth/work/known_good.jsonl; [ $set = broken ] && input=data/synth/work/corrupted.jsonl
      python -m mbla_bench.synth.run judge --endpoint http://127.0.0.1:$port/v1 --model $model --input $input --out data/synth/work/bakeoff/${name}_$set.jsonl 2>&1 | tail -1 | cut -c1-140
    done
    kill $server; wait $server 2>/dev/null
  else
    echo "$name failed to start"; grep -i "error" results/logs/serve_$name.log | tail -2 | cut -c1-200
  fi
  wait $server 2>/dev/null
  port=$((port + 1))
done
