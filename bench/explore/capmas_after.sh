#!/bin/bash
# after capmas_train.sh: retrained CAPMAS on development, cutoffs from development, then final, manifest attack, held-out (D-63)
set -x
cd "$(dirname "$0")/.."
exec >> results/logs/capmas_after.log 2>&1
export PATH=/usr/local/go/bin:$PATH
GPU=${GPU:-0}
until [ -e results/logs/capmas_train/finished ]; do sleep 60; done
.venv/bin/python -m mbla_bench.orchestrate --experiments dev-capmas-retrained --gpus $GPU || exit 1
.venv/bin/python -m mbla_bench.tune --predictions results/raw/dev-capmas-retrained --out results/thresholds_capmas_retrained.json || exit 1
.venv/bin/python -c "
import json
merged = json.load(open('results/thresholds.json')) | json.load(open('results/thresholds_capmas_retrained.json'))
open('results/thresholds.json', 'w').write(json.dumps(merged, indent=2) + '\n')"
make verify || exit 1
.venv/bin/python -m mbla_bench.orchestrate --experiments final-capmas-retrained,final-capmas-retrained-manifest,heldout-capmas-retrained --gpus $GPU
echo "retrained exit $?"
for experiment in dev-capmas-retrained final-capmas-retrained final-capmas-retrained-manifest heldout-capmas-retrained; do
    .venv/bin/python -m mbla_bench.report "$experiment" > "results/logs/report_$experiment.log" 2>&1
done
echo "capmas after done"
