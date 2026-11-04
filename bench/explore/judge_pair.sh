#!/bin/bash
# runs the two chosen judges on a task file (D-40). usage: explore/judge_pair.sh <input> <output>
source .venv/bin/activate
one() { # model revision port input out seqs
  explore/serve_judge.sh $1 $2 $3 1600 $6 > results/logs/serve_pair.log 2>&1 & server=$!; echo $server > results/logs/judge.pid
  until curl -s -m 3 localhost:$3/v1/models > /dev/null || ! kill -0 $server 2>/dev/null; do timeout 5 tail -f /dev/null; done
  python -m mbla_bench.synth.run judge --endpoint http://127.0.0.1:$3/v1 --model $1 --input $4 --out $5 2>&1 | tail -1 | cut -c1-150
  kill $server; wait $server 2>/dev/null
  until [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 1000 ]; do timeout 3 tail -f /dev/null; done
}
one RedHatAI/gemma-4-31B-it-FP8-dynamic d4ab4f579dd3516f97d8a6a4c98d0653480bad15 8150 $1 $2.gemma 3
one casperhansen/llama-3.3-70b-instruct-awq 64d255621f40b42adaf6d1f32a47e1d4534c0f14 8151 $2.gemma $2 3
