#!/bin/bash
# final runs inside a lease of the gpu tool (D-58): prompted helpers, then fine-tuned helpers and held-out families
set -x
cd "$(dirname "$0")/.."
GPUS="${CUDA_VISIBLE_DEVICES:?run this through gpu run}"
PROMPTED=set-only,manifest-only,lexical,random-25,random-50,random-75,capmas,capmas-scores,qwen3-reranker-0.6b,qwen3-reranker-8b,qwen3-1.7b,qwen3-4b,qwen3-8b
make mbla verify || exit 1
.venv/bin/python -m mbla_bench.orchestrate --experiments final,final-manifest --methods "$PROMPTED" --gpus "$GPUS"
echo "prompted exit $?"
.venv/bin/python -m mbla_bench.orchestrate --experiments final-tuned,final-tuned-manifest,heldout --gpus "$GPUS"
echo "tuned exit $?"
for experiment in final final-manifest final-tuned final-tuned-manifest heldout; do
    .venv/bin/python -m mbla_bench.report "$experiment" > "results/logs/report_$experiment.log" 2>&1
done
echo "all done"
