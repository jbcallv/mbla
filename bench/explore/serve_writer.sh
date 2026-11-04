#!/bin/bash
# serves the synthetic task writer on the single available gpu.
export PATH=$PWD/.venv-serve/bin:$PATH CUDA_VISIBLE_DEVICES=0 HF_HOME=/scratch/jbcall/huggingface XDG_CACHE_HOME=/scratch/jbcall/.cache TMPDIR=/scratch/jbcall/tmp
exec vllm serve openai/gpt-oss-20b --revision 6cee5e81ee83917806bbde320786a8fb61efebee --port 8108 --max-model-len 8192 --gpu-memory-utilization 0.85 --seed 0 --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}'
