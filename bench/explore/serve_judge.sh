#!/bin/bash
# serves one judge model on the single available gpu. usage: explore/serve_judge.sh <model> <revision> <port> [max-len] [seqs]
export PATH=$PWD/.venv-serve/bin:$PATH CUDA_VISIBLE_DEVICES=${GPU:-0} HF_HOME=/scratch/jbcall/huggingface XDG_CACHE_HOME=/scratch/jbcall/.cache TMPDIR=/scratch/jbcall/tmp
exec vllm serve $1 --revision $2 --port $3 --max-model-len ${4:-5000} --max-num-seqs ${5:-1} --gpu-memory-utilization 0.98 --seed 0 --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}'
