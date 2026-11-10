# Analysis (final)

Recommended setting, chosen on the development set: **qwen3-4b**

| Ranked helper | Development coverage | Development excess C |
|---|---|---|
| capmas-scores | 0.919 | 0.647 |
| gpt-oss-120b | 0.985 | 0.131 |
| qwen3-30b | 0.904 | 0.128 |
| qwen3-4b | 0.894 | 0.102 |
| qwen3-8b | 0.936 | 0.123 |
| qwen3-reranker-8b | 0.956 | 0.463 |

Coverage non-inferiority (margin 2 points): difference 0.111 [-0.005, 0.231], preserves coverage: True

## F1 (RQ1) best helper vs set-only, excess authority in C

| Comparison | Metric | Templates | Difference | p | p (Holm) |
|---|---|---|---|---|---|
| qwen3-4b vs set-only | excess_C | 8 | -0.800 | 0.0078 | 0.0078 |

## F2 (RQ2) A-bounded vs parent-bounded recovery

| Comparison | Metric | Templates | Difference | p | p (Holm) |
|---|---|---|---|---|---|
| qwen3-4b: A-bounded vs parent-bounded (clean) | attack reachability | 8 | -0.648 | 0.0078 | 0.0156 |
| qwen3-4b: A-bounded vs parent-bounded (injected) | attack reachability | 8 | -0.345 | 0.0156 | 0.0156 |

## F3 best helper vs CAPMAS under our rules and coin flips, excess authority in C

| Comparison | Metric | Templates | Difference | p | p (Holm) |
|---|---|---|---|---|---|
| qwen3-4b vs capmas-scores | excess_C | 8 | -0.554 | 0.0078 | 0.0391 |
| qwen3-4b vs capmas-retrained-bge-large | excess_C | 8 | -0.369 | 0.0156 | 0.0391 |
| qwen3-4b vs random-25 | excess_C | 8 | -0.088 | 0.1016 | 0.1016 |
| qwen3-4b vs random-50 | excess_C | 8 | -0.357 | 0.0078 | 0.0391 |
| qwen3-4b vs random-75 | excess_C | 8 | -0.595 | 0.0078 | 0.0391 |

## F4 (RQ3) benefit retained under attack vs clean

| Comparison | Metric | Templates | Difference | p | p (Holm) |
|---|---|---|---|---|---|
| clean vs attacked (planted) | excess_C | 8 | -0.066 | 0.2344 | 0.2344 |
| clean vs attacked (held-out styles) | excess_C | 8 | -0.151 | 0.0391 | 0.1562 |
| clean vs attacked (inflated manifest) | excess_C | 8 | -0.098 | 0.1094 | 0.2344 |
| clean vs attacked (adaptive, 1000 queries) | excess_C | 8 | -0.106 | 0.0781 | 0.2344 |
