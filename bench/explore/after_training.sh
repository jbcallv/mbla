#!/bin/bash
# after the 8B models: the prompted two-gpu helpers without direct gpu-to-gpu transfer (D-56), then the 8B fine-tuned helpers
cd "$(dirname "$0")/.."
python3 -c "
import json, pathlib
root = pathlib.Path('models/Qwen3-Reranker-8B')
rate = json.loads((root / 'selection.json').read_text())['chosen']
for seed in range(3):
    link = root / f'chosen-seed{seed}'
    link.unlink(missing_ok=True)
    link.symlink_to(f'lr{rate}-seed{seed}')
"
NCCL_P2P_DISABLE=1 timeout 14400 .venv/bin/python -m mbla_bench.orchestrate --experiments dev --methods qwen3-30b,gpt-oss-120b --gpus 0,1
.venv/bin/python -m mbla_bench.orchestrate --experiments dev-tuned --methods qwen3-8b-tuned-s0,qwen3-8b-tuned-s1,qwen3-8b-tuned-s2,qwen3-reranker-8b-tuned-s0,qwen3-reranker-8b-tuned-s1,qwen3-reranker-8b-tuned-s2 --gpus 0,1
