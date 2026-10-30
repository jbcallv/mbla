# Progress against the final methodology

Tracks [`final_methodology.md`](final_methodology.md). Updated with every commit. Status words: **done** (built and
tested), **in progress**, **waiting** (blocked on a person), **planned**.

## Waiting on people

| # | What | Who | Since | Blocks |
|---|---|---|---|---|
| H1 | Approve the labeling guide (`research/labeling_guide.md`) before anyone labels | Joseph (advisor if wanted) | 2026-10-30 | H2, H4 |
| H2 | Development-set review: plans, new candidate rows, attack goals (`bench/data/review/dev/*_alvi.csv`, `*_joseph.csv`) | Alvi, Joseph | 2026-10-30 | tuning cutoffs, choosing the best helper on final labels |
| H3 | Confirm the build output bucket `{owner}-builds` (A-11) with BoundClaw | Joseph → BoundClaw | 2026-10-30 | nothing (easy to change) |
| H4 | Label the final test set blind: candidates and goals first, then correct the draft plans (`bench/data/review/test/*_alvi.csv`, `*_joseph.csv`) | Alvi, Joseph | 2026-10-30 (after H1) | freeze, final runs |
| H5 | After H2 and H4 are adjudicated: confirm 10% of carried tasks (`make label-check SPLIT=dev`, `SPLIT=test`) | one reviewer | – | freeze |

## Order of work (§10)

| Step | Status | Notes |
|---|---|---|
| 1. Convert and relabel the development set | **waiting** (H1, H2) | Converted, validated, report written; human review sheets ready |
| 2. Write, label and freeze the final test set | **waiting** (H1, H4, H5) | 8 templates, 192 tasks, held-out styles written and validated (D-31) |
| 3. Prompted helpers and baselines; deliver helper to BoundClaw | planned | Development runs can start before H2 (labels only change scoring) |
| 4. Training study | planned | After step 3 |

## Components

| Component | Status | Where | Notes |
|---|---|---|---|
| Permission model (C atom forms, destinations, whole volumes, rw covers ro) | done | `mbla/permission.go`, `bench/mbla_bench/reference.py` | Go and Python tests |
| No structured arguments; receiver name and kind in the prompt | done | `mbla/propose.go` | |
| Candidates (narrower grants for named resources, no volumes for remote receivers) | done | `mbla/propose.go`, `bench/mbla_bench/answer.py` | Go and Python lists identical on all 408 development tasks |
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
| Reporting (tables, figures, Holm families, per handoff) | planned | | `report.py`, `export.py`, `significance.py`, `judge.py` still use the pilot format |
| Helper configuration for the final helper list (drop Laya, CLM, other sizes) | planned | `bench/config/` | |
| CAPMAS under our rules in the new format | planned | | |
| Adaptive attacker; inflated-manifest attack | planned | | |
| Synthetic generator, mock execution, injection writer | planned | `bench/mbla_bench/synth/` | Labeler and judges exist (pilot format) |
| Training | planned | | |

## Log

- **2026-10-30** · D-30. Final methodology in markdown; library, benchmark, simulator, metrics and tuning moved to the final rules; development set converted (408 tasks, 120 task-goals dropped by reason, 0 unavoidable); pilot human labels checked against the new keys (183 mapped, 6 explained differences); labeling guide and review sheets ready.
- **2026-10-30** · D-31. Final test set written: 8 templates, 192 tasks, 48 held-out-style injections (four AgentDojo/InjecAgent styles, 12 each); blind review sheets ready.
