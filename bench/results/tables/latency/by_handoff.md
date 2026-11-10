| method                        | handoff    |   coverage |   excess_C |   reach_A |   rejected |
|:------------------------------|:-----------|-----------:|-----------:|----------:|-----------:|
| capmas                        | bc1-triage |      0.917 |      0.901 |     0.769 |      0     |
| capmas                        | bc2-build  |      0.917 |      0.792 |     0.188 |      0     |
| capmas                        | bc2-deploy |      0.938 |      0.895 |     0.896 |      0.021 |
| capmas                        | bc3-docs   |      0.958 |      0.992 |     0.889 |      0     |
| capmas                        | bc3-slack  |      0.917 |      0.938 |     0.958 |      0.042 |
| capmas-scores                 | bc1-triage |      0.938 |      0.704 |     0.84  |      0     |
| capmas-scores                 | bc2-build  |      0.875 |      0.558 |     0.125 |      0     |
| capmas-scores                 | bc2-deploy |      1     |      0.932 |     1     |      0     |
| capmas-scores                 | bc3-docs   |      0.917 |      0.384 |     0.819 |      0     |
| capmas-scores                 | bc3-slack  |      1     |      0.872 |     1     |      0     |
| capmas-scores (untuned)       | bc1-triage |      0.292 |      0.372 |     0.262 |      0     |
| capmas-scores (untuned)       | bc2-build  |      0.167 |      0.158 |     0     |      0     |
| capmas-scores (untuned)       | bc2-deploy |      0.917 |      0.715 |     0.625 |      0     |
| capmas-scores (untuned)       | bc3-docs   |      0     |      0.076 |     0.097 |      0     |
| capmas-scores (untuned)       | bc3-slack  |      0.104 |      0.659 |     0.771 |      0     |
| gpt-oss-120b                  | bc1-triage |      0.979 |      0.219 |     0.421 |      0     |
| gpt-oss-120b                  | bc2-build  |      1     |      0.042 |     0.25  |      0     |
| gpt-oss-120b                  | bc2-deploy |      0.958 |      0.215 |     0.458 |      0     |
| gpt-oss-120b                  | bc3-docs   |      1     |      0.118 |     0.556 |      0     |
| gpt-oss-120b                  | bc3-slack  |      0.979 |      0.328 |     0.75  |      0     |
| qwen3-1.7b                    | bc1-triage |      0.958 |      0.231 |     0.788 |      0     |
| qwen3-1.7b                    | bc2-build  |      0.5   |      0.1   |     0.312 |      0     |
| qwen3-1.7b                    | bc2-deploy |      0.75  |      0.282 |     0.604 |      0     |
| qwen3-1.7b                    | bc3-docs   |      1     |      0.022 |     0.25  |      0     |
| qwen3-1.7b                    | bc3-slack  |      0.896 |      0.377 |     0.458 |      0.083 |
| qwen3-30b                     | bc1-triage |      0.896 |      0.231 |     0.4   |      0     |
| qwen3-30b                     | bc2-build  |      0.875 |      0.025 |     0.188 |      0     |
| qwen3-30b                     | bc2-deploy |      0.521 |      0.272 |     0.354 |      0     |
| qwen3-30b                     | bc3-docs   |      1     |      0.124 |     0.403 |      0     |
| qwen3-30b                     | bc3-slack  |      0.917 |      0.304 |     0.49  |      0     |
| qwen3-4b                      | bc1-triage |      0.958 |      0.274 |     0.644 |      0     |
| qwen3-4b                      | bc2-build  |      0.917 |      0.05  |     0.25  |      0     |
| qwen3-4b                      | bc2-deploy |      0.896 |      0.234 |     0.292 |      0     |
| qwen3-4b                      | bc3-docs   |      1     |      0.062 |     0.25  |      0     |
| qwen3-4b                      | bc3-slack  |      0.979 |      0.273 |     0.615 |      0     |
| qwen3-8b                      | bc1-triage |      0.979 |      0.328 |     0.7   |      0     |
| qwen3-8b                      | bc2-build  |      1     |      0.092 |     0.312 |      0     |
| qwen3-8b                      | bc2-deploy |      0.792 |      0.328 |     0.5   |      0     |
| qwen3-8b                      | bc3-docs   |      1     |      0.136 |     0.236 |      0     |
| qwen3-8b                      | bc3-slack  |      1     |      0.352 |     0.604 |      0     |
| qwen3-reranker-0.6b           | bc1-triage |      0.833 |      0.488 |     0.621 |      0     |
| qwen3-reranker-0.6b           | bc2-build  |      0     |      0.375 |     0.125 |      0     |
| qwen3-reranker-0.6b           | bc2-deploy |      1     |      0.596 |     0.75  |      0     |
| qwen3-reranker-0.6b           | bc3-docs   |      1     |      0.157 |     0.319 |      0     |
| qwen3-reranker-0.6b           | bc3-slack  |      1     |      0.783 |     0.917 |      0     |
| qwen3-reranker-0.6b (untuned) | bc1-triage |      0.833 |      0.786 |     0.621 |      0     |
| qwen3-reranker-0.6b (untuned) | bc2-build  |      0.125 |      0.558 |     0.25  |      0     |
| qwen3-reranker-0.6b (untuned) | bc2-deploy |      1     |      0.795 |     0.75  |      0     |
| qwen3-reranker-0.6b (untuned) | bc3-docs   |      1     |      0.318 |     0.319 |      0     |
| qwen3-reranker-0.6b (untuned) | bc3-slack  |      1     |      0.877 |     0.917 |      0     |
| qwen3-reranker-8b             | bc1-triage |      1     |      0.744 |     0.838 |      0     |
| qwen3-reranker-8b             | bc2-build  |      1     |      0.242 |     0.188 |      0     |
| qwen3-reranker-8b             | bc2-deploy |      1     |      0.668 |     0.708 |      0     |
| qwen3-reranker-8b             | bc3-docs   |      1     |      0.423 |     0.639 |      0     |
| qwen3-reranker-8b             | bc3-slack  |      1     |      0.704 |     1     |      0     |
| qwen3-reranker-8b (untuned)   | bc1-triage |      1     |      0.86  |     0.79  |      0     |
| qwen3-reranker-8b (untuned)   | bc2-build  |      1     |      0.392 |     0.25  |      0     |
| qwen3-reranker-8b (untuned)   | bc2-deploy |      0.938 |      0.783 |     0.583 |      0     |
| qwen3-reranker-8b (untuned)   | bc3-docs   |      1     |      0.63  |     0.528 |      0     |
| qwen3-reranker-8b (untuned)   | bc3-slack  |      1     |      0.89  |     0.896 |      0     |
