"""scorer cutoffs on the development set only (final methodology §4, D-29)."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from mbla_bench import answer, data, metrics, simulate

GRID = [round(step * 0.05, 2) for step in range(1, 21)]
TUNING_CAP = 3
TARGET_COVERAGE = 0.98


def mean(values):
    return sum(values) / len(values) if values else 0.0


def dev_f1(rows, items, keys, initial):
    return mean([metrics.f1(metrics.item_metrics(items[row["item"]], simulate.with_thresholds(row, initial, initial), required=keys[row["item"]])) for row in rows])


def dev_coverage(rows, items, keys, initial, admit):
    outcomes = []
    for row in rows:
        chosen = simulate.with_thresholds(row, initial, admit)
        outcomes.append(simulate.simulate(items[row["item"]], chosen, "A-bounded", TUNING_CAP, required=keys[row["item"]])["covered"])
    return mean(outcomes)


def tune_method(rows, items, keys):
    best_initial = max(GRID, key=lambda threshold: (dev_f1(rows, items, keys, threshold), threshold))
    coverage = {threshold: dev_coverage(rows, items, keys, best_initial, threshold) for threshold in GRID if threshold <= best_initial}
    meeting = [threshold for threshold, value in coverage.items() if value >= TARGET_COVERAGE]
    best_admit = max(meeting) if meeting else max(coverage, key=lambda threshold: (coverage[threshold], threshold))
    return {
        "initial": best_initial,
        "admit": best_admit,
        "meets_target": bool(meeting),
        "dev_f1": dev_f1(rows, items, keys, best_initial),
        "dev_coverage": coverage[best_admit],
        "dev_rows": len(rows),
    }


def main():
    parser = argparse.ArgumentParser(description="choose scorer cutoffs on the development set only")
    parser.add_argument("--predictions", default="results/raw/dev")
    parser.add_argument("--items", default="data/tasks/dev.jsonl")
    parser.add_argument("--out", default="results/thresholds.json")
    arguments = parser.parse_args()
    items = data.items_by_id(arguments.items)
    keys = {item_id: answer.tiers(item)[0] for item_id, item in items.items()}
    models = data.load_yaml("config/models.yaml")["methods"]
    rows_by_method = defaultdict(list)
    for row in data.load_predictions(arguments.predictions):
        method = models.get(row["method"], {})
        if row["input"] == "full" and method.get("paradigm") in ("decision", "embedding", "capmas") and "fixed_thresholds" not in method:
            rows_by_method[row["method"]].append(row)
    chosen = {method: tune_method(rows, items, keys) for method, rows in sorted(rows_by_method.items())}
    Path(arguments.out).write_text(json.dumps(chosen, indent=2) + "\n")
    print(json.dumps(chosen, indent=2))


if __name__ == "__main__":
    main()
