#!/usr/bin/env bash
# starts the mbla helper on the pod: /score and the mbla chat format, on 0.0.0.0:8300, key required.
cd /workspace/mbla/bench
[ -x /workspace/venv/bin/python ] || { python -m venv --system-site-packages /workspace/venv && /workspace/venv/bin/pip install -q transformers==5.18.0 tokenizers==0.23.2 safetensors==0.8.0; }
setsid nohup /workspace/venv/bin/python serve/decision_server.py --backend qwen3-reranker \
  --model /workspace/mbla/models/reranker-8b-tuned-s1 --host 0.0.0.0 --port 8300 \
  --api-key-file /workspace/mbla/api_key --chat-names mbla-reranker-8b-tuned mbla-qwen3-4b-tuned Qwen/Qwen3-8B \
  --cutoffs 0.7 0.15 > /workspace/mbla/server.log 2>&1 < /dev/null &
echo started $!
