# Progress against the final methodology

Tracks [`final_methodology.md`](final_methodology.md). Updated with every commit. Status words: **done** (built and
tested), **in progress**, **waiting** (blocked on a person), **planned**.

## Waiting on people

Open as of 2026-11-09. Older items (labeling, reviews, first GPU access) are closed; see the decisions log.

| # | What | Who | Since | Blocks |
|---|---|---|---|---|
| J1 | GPUs for Qwen3-30B and gpt-oss-120b: cards 0+1 fault on transfers between them (D-55 to D-57). Ask for cards 2+3 (same NUMA side, other link) in place of 0+1 once our runs finish; run the copy test first. `gpu status`: cap 2 per person, 2 and 3 leased by Zaiyu Cheng | Joseph → admins | 2026-11-09 | 30B, gpt-oss-120b |
| J2 | Qwen3-30B on one card in FP8 (disclosed precision change), if no working pair | Joseph | 2026-11-09 | 30B fallback |
| J3 | Review the adaptive attacker's design (D-62), then "go" for its final-test run | Joseph | 2026-11-09 | attack (c) on the final test, F4 |
| J4 | Answer order (D-64): option (b) chosen, a development-only check; after it, decide (a) disclose or (c) retrain | Joseph | 2026-11-09 | fine-tuned results' reading |
| J5 | What the security team receives: prompted Qwen3-4B (recommended) or fine-tuned Qwen3-4B seed 2 (D-59, D-60) | Joseph | 2026-11-09 | BoundClaw package |
| J6 | Ask BoundClaw whether their adapter also sends the schema with keys sorted (plausible first) (D-64) | Joseph → BoundClaw | 2026-11-09 | reading of D-64 |

## Order of work (§10)

| Step | Status | Notes |
|---|---|---|
| 1. Convert and relabel the development set | **waiting** (H1, H2) | Converted, validated, report written; human review sheets ready |
| 2. Write, label and freeze the final test set | **waiting** (H1, H4, H5) | 8 templates, 192 tasks, held-out styles written and validated (D-31) |
| 3. Prompted helpers and baselines; deliver helper to BoundClaw | **in progress**, model helpers waiting (H6) | CPU baselines run on the development set; report and analysis built. Development runs need no labels to start (labels only change scoring) |
| 4. Training study | planned | After step 3 |

## Components

| Component | Status | Where | Notes |
|---|---|---|---|
| Permission model (C atom forms, destinations, whole volumes, rw covers ro) | done | `mbla/permission.go`, `bench/mbla_bench/reference.py` | Go and Python tests |
| No structured arguments; the prompt shows the task text and manifest only (D-33) | done | `mbla/propose.go` | |
| Candidates (narrower grants for named resources, no volumes for remote receivers, read-write folders also offered read-only) | done | `mbla/propose.go`, `bench/mbla_bench/answer.py` | Go and Python lists identical on all 408 development tasks |
| Ceiling check; recovery rules (volume denials final, destinations within ceiling, k counts requests) | done | `mbla/check.go`, `mbla/recovery.go` | |
| Answer keys from plans; unavoidable goals | done | `bench/mbla_bench/answer.py` | |
| Simulator: any-plan coverage, refusals, ceiling rejections, A- vs parent-bounded recovery | done | `bench/mbla_bench/simulate.py` | Oracle: coverage 100%, excess 0 |
| Metrics per component vs least-authority plan, decoy rate, undefined cases | done | `bench/mbla_bench/metrics.py` | |
| Cutoff tuning: grid 0.05–1, 98% coverage target, flag if unmet | done | `bench/mbla_bench/tune.py` | |
| Sign-flip permutation test on template means | done | `bench/mbla_bench/stats.py` | Exact up to 20 templates; 8 templates → min p = 1/128 |
| Converted development set (408 tasks) | done, labels under review | `bench/data/templates/`, `bench/data/tasks/dev.jsonl` | `research/conversion_report.md` |
| Labeling guide | done, awaiting approval (H1) | `research/labeling_guide.md` | |
| Labeling sheets and agreement (κ, unclear, disagreements) | done | `bench/mbla_bench/labels.py` | |
| Final test set: 8 templates, held-out injection styles | done, labels pending (H4) | `bench/data/templates/test.yaml`, `injection_styles.yaml`, `bench/data/tasks/test.jsonl` | Not frozen; no helper may run on it |
| 10% carried-label check | done | `bench/mbla_bench/labels.py` (`carried-check`) | |
| Reporting (summary with intervals, per handoff/breadth/style, k sensitivity, undefined counts, untuned scorers) | done | `bench/mbla_bench/report.py` | Run on the CPU baselines |
| Analysis plan (best helper, F1–F4 with Holm, non-inferiority) | done | `bench/mbla_bench/analysis.py` | F5 with training |
| Helper inputs match BoundClaw's adapter: task text, manifest, bare candidates (D-33) | done | `mbla/propose.go`, `bench/config/experiments.yaml` | |
| Helper configuration for the final helper list; 45 s budget | done | `bench/config/experiments.yaml`, `mbla/cmd/mbla/scorer.go` | |
| Attack (d) inflated manifest | done | `bench/mbla_bench/attacks.py`, `data/attacks/` | Clean tasks only |
| Conformance of the Go checker on the new forms | done | `bench/mbla_bench/conform.py` | 14,440 pairs, 0 disagreements |
| FORTIS harness on the new library | done | `bench/mbla_bench/fortis.py` | Smoke-tested with CPU baselines |
| CAPMAS under our rules in the new format | planned | | |
| Adaptive attacker (attack (c)) | planned | | Needs GPUs (H6) |
| Synthetic generator, mock execution, injection writer | in progress | `bench/mbla_bench/synth/` | Moved to the final format; 4,915 tasks written, 2,779 passed mock execution, two judges next; 93-task sheet code ported (`synth/audit.py`) |
| Training | code ready, waiting for the 93-task check | `bench/mbla_bench/train.py`, `synth/capmas_export.py` | Tested on small runs only (2026-11-05): generative and reranker on an 80-task slice, QLoRA code path on Qwen3-1.7B, CAPMAS's own trainer for one epoch; all test weights deleted. QLoRA not yet run on Qwen3-30B itself |

## Log

- **2026-10-30** · D-30. Final methodology in markdown; library, benchmark, simulator, metrics and tuning moved to the final rules; development set converted (408 tasks, 120 task-goals dropped by reason, 0 unavoidable); pilot human labels checked against the new keys (183 mapped, 6 explained differences); labeling guide and review sheets ready.
- **2026-10-30** · D-31. Final test set written: 8 templates, 192 tasks, 48 held-out-style injections (four AgentDojo/InjecAgent styles, 12 each); blind review sheets ready.
- **2026-10-30** · D-32. Helper list and experiments set; report and analysis built; attack (d) derived; conformance re-run (0 disagreements); FORTIS moved to the new schema; CPU baselines run on the development set. GPUs on ams1 are down (H6).
- **2026-11-02** · D-33. BoundClaw's Nov 2 review: the helper now sees only the task text, the manifest and bare numbered permissions; methodology Table 1, §5, §7 and §12 updated. Sample tasks for BoundClaw written (`boundclaw_samples.md`). Open: scorers and gpt-oss under the adapter (H7).
- **2026-11-02** · D-34. Read-write folders also offered read-only, as BoundClaw's adapter does; answer keys, review sheets and CPU baselines regenerated; pilot label carrying fixed. Open with BoundClaw: narrower candidates for named resources (H8).
- **2026-11-03** · H6 re-diagnosed: the GPUs work but are reserved by access list for two other users; we need an allocation, not a repair.
- **2026-11-03** · Access granted to GPU device 1 (ACL); CUDA sees one L40S.
- **2026-11-03** · First development runs on one GPU: Qwen3 1.7B, 4B, 8B, both rerankers, CAPMAS (0 errors). CAPMAS under our rules added to tuning. No helper meets 98% coverage, mainly because missing folders cannot be requested (F-30). Provisional: labels unreviewed.
- **2026-11-04** · D-35. Deadline 2026-11-18; fine-tuning stays; gpt-oss-120b and Qwen3-30B skipped without a second GPU. Exploratory input comparison on the development set under way (`bench/explore/`, `bench/results/explore/`).
- **2026-11-04** · D-36. One blind review sheet (127 rows) and a judge model, checked against the human sheet.
- **2026-11-04** · D-37. Answer-key rules settled from Joseph's review; 600 tasks regenerated, oracle coverage 408/408 and 192/192.
- **2026-11-04** · D-38. Llama-3.3-70B judge: κ lower bound 0.547, under the 0.6 rule; threshold not moved, so a human labels the remaining 107 rows (`share/review_sheet_2.csv`). Waiting on Joseph.
- **2026-11-04** · Cutoffs tuned on 2026-11-03 used unreviewed keys and are invalid (F-30); they will be re-set on reviewed keys.
- **2026-11-04** · Synthetic generation by gpt-oss-20b (one GPU, per D-35): 1,072 requests, 4,915 tasks, 89 failed requests, 2,779 passed mock execution, 0 removed by the 8-word and near-duplicate filters (checked: closest pair 0.78 against the 0.8 cutoff). The judge stage now runs at temperature 0 and counts failed requests apart from rejections.
- **2026-11-05** · GPU device 0 now open to us, shared with ben. Models for the synthetic set chosen by a fixed test (D-40): writer gpt-oss-20b, judges Gemma 4 31B and Llama-3.3-70B; set being rebuilt.
- **2026-11-05** · D-41, D-42. Six F5 tests; model second reader; synthetic set frozen at 1,966 tasks; blind 93-task sheet (1,136 rows) sent to Joseph.
