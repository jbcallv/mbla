#!/bin/bash
# gemma, the chosen second reader, labels the synthetic check sheet on gpu 1 (D-47).
source .venv/bin/activate
export GPU=1
port=8170 model=RedHatAI/gemma-4-31B-it-FP8-dynamic
revision=$(ls /scratch/jbcall/huggingface/hub/models--${model//\//--}/snapshots | head -1)
explore/serve_judge.sh $model $revision $port 5000 1 > results/logs/serve_label_synth.log 2>&1 & server=$!
until curl -s -m 3 localhost:$port/v1/models > /dev/null || ! kill -0 $server 2>/dev/null; do timeout 5 tail -f /dev/null; done
python -m mbla_bench.synth.audit_label --endpoint http://127.0.0.1:$port/v1 --model $model
kill $server; wait $server 2>/dev/null
