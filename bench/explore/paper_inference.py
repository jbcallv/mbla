"""table rows and figure points for the paper's policy-inference subsection, from the final-test result tables."""
import csv
import json
import statistics
import sys
from pathlib import Path

import numpy as np

OUT = Path(sys.argv[1])
TABLES = Path("results/tables")
RAW = Path("results/raw")

BASELINES = [("set-only", "Set-only (parent)"), ("manifest-only", "Manifest-only"), ("lexical", "Lexical"),
             ("capmas-scores", "CAPMAS")]
PROMPTED = [("qwen3-1.7b", "Qwen3-1.7B"), ("qwen3-4b", "Qwen3-4B"), ("qwen3-8b", "Qwen3-8B"),
            ("qwen3-30b", "Qwen3-30B-A3B"), ("gpt-oss-120b", "gpt-oss-120b"),
            ("qwen3-reranker-0.6b", "Reranker-0.6B"), ("qwen3-reranker-8b", "Reranker-8B")]
TUNED = [("qwen3-1.7b-tuned", "Qwen3-1.7B"), ("qwen3-4b-tuned", "Qwen3-4B"), ("qwen3-8b-tuned", "Qwen3-8B"),
         ("qwen3-reranker-0.6b-tuned", "Reranker-0.6B"), ("qwen3-reranker-8b-tuned", "Reranker-8B")]


def rows(name):
    with open(TABLES / name / "summary.csv") as f:
        return {row["method"]: row for row in csv.DictReader(f)}


def point(text):
    return float(text.split(" ")[0])


def latency(pattern):
    """median and 99th percentile over every call of every run, from the raw rows (gpu runs only)."""
    calls = [json.loads(line)["latency_ms"] for path in sorted(RAW.glob(pattern)) for line in open(path)]
    return (0.0, 0.0) if not calls or None in calls else tuple(float(np.percentile(calls, q)) for q in (50, 99))


def values(row):
    return {"cov": point(row["coverage"]), "eac_c": point(row["excess_C"]), "eac_n": float(row["excess_plain"]),
            "eac_d": float(row["excess_D"]), "mac_c": float(row["missing_C"]),
            "p50": 0.0, "p99": 0.0}


def with_latency(v, pattern):
    v["p50"], v["p99"] = latency(pattern)
    return v


def seeds_mean(table, prefix):
    runs = [values(table[f"{prefix}-s{seed}"]) for seed in range(3)]
    mean = {key: statistics.mean(run[key] for run in runs) for key in runs[0]}
    with_latency(mean, f"final-tuned/{prefix}-s*__full__s0.jsonl")
    spread = {key: (min(run[key] for run in runs), max(run[key] for run in runs)) for key in runs[0]}
    return mean, spread


def ms(value):
    return "$<$1" if value < 1 else f"{value:,.0f}"


def line(label, v, spread=None):
    cov = f"{100 * v['cov']:.0f}"
    eac = f"{v['eac_c']:.2f}"
    if spread:
        cov += f"\\,\\scriptsize({100 * spread['cov'][0]:.0f}--{100 * spread['cov'][1]:.0f})"
        eac += f"\\,\\scriptsize({spread['eac_c'][0]:.2f}--{spread['eac_c'][1]:.2f})"
    return (f"{label} & {cov} & {eac} & {v['eac_n']:.2f} & {v['eac_d']:.2f} & {v['mac_c']:.2f} & "
            f"{ms(v['p50'])} & {ms(v['p99'])} \\\\\n")


final, tuned = rows("final"), rows("final-tuned")
table, points = "", "label kind latency eac cov\n"
for key, label in BASELINES:
    table += line(label, with_latency(values(final[key]), f"final/{key}__full__s*.jsonl"))
table += "\\midrule\n\\multicolumn{8}{@{}l}{\\emph{Prompted helpers}} \\\\\n"
for key, label in PROMPTED:
    v = with_latency(values(final[key]), f"final/{key}__full__s*.jsonl")
    table += line(label, v)
    points += f"{label} prompted {v['p50']} {v['eac_c']} {v['cov']}\n"
table += "\\midrule\n\\multicolumn{8}{@{}l}{\\emph{Fine-tuned helpers (mean of three training seeds, range)}} \\\\\n"
for key, label in TUNED:
    v, spread = seeds_mean(tuned, key)
    table += line(label, v, spread)
    points += f"{label} tuned {v['p50']} {v['eac_c']} {v['cov']}\n"
v = with_latency(values(final["capmas-scores"]), "final/capmas-scores__full__s*.jsonl")
points += f"CAPMAS baseline {v['p50']} {v['eac_c']} {v['cov']}\n"

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "table.tex").write_text(table)
(OUT / "points.dat").write_text(points)
print(table)
print(points)
