#!/bin/bash
# cards 0+1 (2026-11-10, D-65): the copy fault no longer shows, so the two-card helpers run, then card 0's retrained CAPMAS.
# a watchdog stops a model whose server log is silent for 15 minutes (the D-56/D-57 hang) so nothing is left holding the cards.
cd "$(dirname "$0")/.."
exec > >(tee -a results/logs/pair_chain.log) 2>&1
export PATH=/usr/local/go/bin:$PATH
EXPERIMENTS=dev,dev-manifest,final,final-manifest,mostargate,fortis1,fortis2,latency
make mbla verify || { echo "verify exit 1"; exit 1; }

stop_port() {
    for pid in $(ps -u "$USER" -o pid,args | grep "[v]llm serve.*--port $1" | awk '{print $1}'); do kill -- -"$(ps -o pgid= -p "$pid" | tr -d ' ')" 2>/dev/null; done
}

run_pair() {
    local method=$1 port=$2 log=results/logs/$1.log
    touch "$log"
    .venv/bin/python -m mbla_bench.orchestrate --experiments "$EXPERIMENTS" --methods "$method" --gpus 0,1 &
    local runner=$!
    while kill -0 "$runner" 2>/dev/null; do
        sleep 60
        if [ $(( $(date +%s) - $(stat -c %Y "$log") )) -gt 900 ]; then
            echo "HANG $method: server log silent 15 min, stopping"
            kill "$runner"; stop_port "$port"; wait "$runner"; return 1
        fi
    done
    wait "$runner"; local code=$?
    stop_port "$port"
    echo "$method exit $code"
    return $code
}

HF_HOME=/scratch/jbcall/huggingface .venv-serve/bin/hf download Qwen/Qwen3-30B-A3B --revision ad44e777bcd18fa416d9da3bd8f70d33ebb85d39 > results/logs/download_30b.log 2>&1 || { echo "download exit 1"; exit 1; }
run_pair qwen3-30b 8110
run_pair gpt-oss-120b 8109
GPU=0,1 bash explore/capmas_after.sh
echo "pair chain done"
