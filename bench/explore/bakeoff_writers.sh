#!/bin/bash
# each writer candidate writes the same small trial with the same prompt (D-40). usage: explore/bakeoff_writers.sh
source .venv/bin/activate
mkdir -p data/synth/work/bakeoff
trial() { # name model
  until curl -s -m 3 localhost:$3/v1/models > /dev/null || ! kill -0 $server 2>/dev/null; do timeout 5 tail -f /dev/null; done
  rm -f data/synth/work/bakeoff/raw_$1.jsonl
  python -m mbla_bench.synth.run write --endpoint http://127.0.0.1:$3/v1 --model $2 --scale 0.1 --raw data/synth/work/bakeoff/raw_$1.jsonl 2>&1 | tail -1 | cut -c1-140
  kill $server; wait $server 2>/dev/null
  wait $server 2>/dev/null
}
explore/serve_writer.sh > results/logs/serve_w_gptoss.log 2>&1 & server=$!; echo $server > results/logs/writer.pid
trial gptoss openai/gpt-oss-20b 8108
explore/serve_judge.sh ibm-granite/granite-4.2-30b-fp8 bee6d7463fd7064455f59ac480a3fcdcae5cb801 8140 8192 8 > results/logs/serve_w_granite.log 2>&1 & server=$!; echo $server > results/logs/writer.pid
trial granite ibm-granite/granite-4.2-30b-fp8 8140
explore/serve_judge.sh unsloth/GLM-4.7-Flash-FP8-Dynamic 1174de1393d38e3d30c2882b98eb54fd8c1e9d1f 8141 8192 8 > results/logs/serve_w_glm.log 2>&1 & server=$!; echo $server > results/logs/writer.pid
trial glm unsloth/GLM-4.7-Flash-FP8-Dynamic 8141
