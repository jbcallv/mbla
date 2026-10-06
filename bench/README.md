# MBLA replication package

Reproduces every MBLA result for the BoundClaw paper. Predictions come from the same Go code the enforcement layer imports (`../mbla`). Python only generates data, simulates recovery, and computes metrics and statistics.

## Setup

```
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
make mbla
```

Model serving needs a separate environment (`python3 -m venv .venv-serve && .venv-serve/bin/pip install vllm laya contrastive-lm`) and GPUs; `orchestrate.py` starts each model's server from `config/models.yaml`. Hosted models read keys from `MBLA_API_KEY` (scorers) and `JUDGE_API_KEY` (judge).

## Order of work

| Step | Command | Output | Notes |
|---|---|---|---|
| 1. Build and test the core package | `make mbla` | `../mbla/bin/mbla` | |
| 2. Generate and validate items | `make data` | `data/tasks/{dev,test}.jsonl` | deterministic |
| 3. Audit references | `make review-sheets REVIEWERS="a b"`, fill, `make review-compare REVIEWERS="a b"`, resolve, `make review-final` | `data/review/` | see below |
| 4. Freeze test | `make freeze` | `data/tasks/SHA256SUMS` | before any test run |
| 5. Checker conformance (E7) | `make conform` | `results/tables/conformance.json` | false accept and reject rates must be 0 |
| 6. Download models | `bash serve/download.sh` | HF cache on scratch | revisions pinned in `config/models.yaml` |
| 7. Dev predictions | `make dev` | `results/raw/dev/` | `orchestrate.py` serves each model alone, runs it, stops it |
| 8. Tune thresholds on dev | `make tune` | `results/thresholds.json` | pre-registered objective (D-12) |
| 9. Test predictions | `make e1 e3 e4 fortis` (add `SHARED=--shared` on a busy machine) | `results/raw/e*/`, `results/raw/fortis*/` | refuses to run if the test split changed since freeze |
| 10. Latency (E5) | `make e5` | `results/raw/e5/` | always exclusive GPUs; the only source of latency numbers (D-18) |
| 11. Tables, significance | `make report significance` | `results/tables/` | cluster bootstrap over templates, Holm correction |
| 12. Judge (E8, optional) | `make judge judge-adjust` | `results/raw/judge.jsonl`, `results/tables/e1_judge_adjusted.json` | validation sheet `data/review/judge_sample.csv` |
| 13. Figures and report | `make figures` | `../plots/out/`, `../report/mbla_findings.pdf` | gnuplot and LaTeX |

Every run appends a line to `results/runs.md`.

## Reference audit

References come from 17 templates, so the audit is per template, not per item.

1. `make review-sheets REVIEWERS=alice,bob` writes `data/review/audit_alice.csv` and `audit_bob.csv`. Each has 185 rows: every candidate permission for one example of each template.
2. Each reviewer fills `needed` with `1`/`yes`, `0`/`no`, or `unclear`, on their own, without looking at the other sheet or at `tasks.yaml`. The `note` column is optional.
3. `make review-compare REVIEWERS="alice bob"` (one or more names) prints Cohen's kappa for every pair, including the current references (`author`), skipping `unclear` rows, and writes `data/review/audit_disagreements.csv` with every row where anyone differs or is unclear.
4. Fill the `resolved` column of `audit_disagreements.csv` (never edit the rater sheets: agreement is reported on independent labels, frozen in `results/tables/reference_audit_independent.json`).
5. Edit `reference:` in `data/templates/tasks.yaml` (or `baseline:`/`runtime:` in `delegations.yaml`), run `make data`, then `make review-final`. It writes `data/review/audit_final.csv` and fails if any generated reference differs from the final labels.
6. `make freeze`.

The E8 judge review is separate and comes after the model runs: `make judge` writes `data/review/judge_sample.csv` (150 rows).

## What each table answers

| File | Experiment | Question |
|---|---|---|
| `e1_quality` | E1 | M1: excess (EAC) and missing (MAC) authority per component, exact match, size |
| `e1_recovery` | E6 | M3: benign success, recoveries, and attack surface (RAS) before and after recovery, `bound-only` vs `admitted`, caps 1/3/5 |
| `e1_by_variant` | E9 | EAC/MAC on injection vs benign items |
| `e1_latency` | E5 | M2: p50/p95/p99 latency, $ per 1k delegations, failure rate |
| `e1_operating_curves.pdf` | E2 | capability EAC vs MAC as the initial threshold sweeps |
| `e3_quality` | E3 | M4: input ablation (text, +args, +history, +manifest) |
| `e4_quality` | E4 | M5: CLM vs Qwen3-8B on the same backbone |
| `conformance.json` | E7 | Go checker vs independent set-semantics reference |
| `fortis1_fortis_metrics.json`, `fortis2_...` | external | FORTIS exact match, over-privilege, no-action, safe rate per method |

## Rules that keep results sound

- Thresholds are chosen on dev only (`tune.py`):
  - initial threshold: maximizes mean F1 against the reference;
  - admit threshold: the tightest value keeping simulated benign success ≥ 95% under `admitted` with cap 3.
- The test split is frozen by hash, and `make e1` checks the hash first.
- Templates are the split and clustering unit. All confidence intervals are cluster bootstraps over templates.
- Failures and parse errors count as empty grants and are never dropped.
- Go and Python must agree on threshold selection for every row; `report.py` exits if they don't.
- The judge only labels prediction-vs-reference differences. Deterministic metrics are always reported unadjusted.

## Layout

```
config/       models and experiments (pin versions here)
data/         universe.json, templates/, tasks/ (generated), review/ (human labels)
serve/        download script and the /score decision-model server
mbla_bench/   generate, validate, review, reference, conform, orchestrate, run, tune, simulate, metrics, stats, significance, fortis, judge, report, export
results/      tables/, thresholds.json, runs.md, archive/harness_v1/ (raw/ is a release asset)
tests/        unit tests for metrics, simulation and statistics
```
