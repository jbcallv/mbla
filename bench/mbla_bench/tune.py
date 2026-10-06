import argparse
import json
from collections import defaultdict
from pathlib import Path

from mbla_bench import data, metrics, simulate

GRID = [round(step * 0.05, 2) for step in range(21)]
TUNING_CAP = 3
TARGET_SUCCESS = 0.95


def mean(values):
    return sum(values) / len(values) if values else 0.0


def dev_f1(rows, items, initial):
    return mean([metrics.f1(metrics.item_metrics(items[row["item"]], simulate.with_thresholds(row, initial, initial))) for row in rows])


def dev_success(rows, items, initial, admit):
    outcomes = []
    for row in rows:
        chosen = simulate.with_thresholds(row, initial, admit)
        outcomes.append(simulate.simulate(items[row["item"]], chosen, "admitted", TUNING_CAP)["success"])
    return mean(outcomes)


def tune_method(rows, items):
    best_initial = max(GRID, key=lambda threshold: (dev_f1(rows, items, threshold), threshold))
    admit_options = [
        threshold for threshold in GRID if threshold <= best_initial and dev_success(rows, items, best_initial, threshold) >= TARGET_SUCCESS
    ]
    best_admit = max(admit_options) if admit_options else min(GRID)
    return {
        "initial": best_initial,
        "admit": best_admit,
        "dev_f1": dev_f1(rows, items, best_initial),
        "dev_success": dev_success(rows, items, best_initial, best_admit),
        "dev_rows": len(rows),
    }


def main():
    parser = argparse.ArgumentParser(description="choose thresholds per method on the dev split only")
    parser.add_argument("--predictions", default="results/raw/dev")
    parser.add_argument("--items", default="data/tasks/dev.jsonl")
    parser.add_argument("--out", default="results/thresholds.json")
    arguments = parser.parse_args()
    items = data.items_by_id(arguments.items)
    rows_by_method = defaultdict(list)
    for row in data.load_predictions(arguments.predictions):
        if row["input"] == "full":
            rows_by_method[row["method"]].append(row)
    chosen = {method: tune_method(rows, items) for method, rows in sorted(rows_by_method.items())}
    Path(arguments.out).write_text(json.dumps(chosen, indent=2) + "\n")
    print(json.dumps(chosen, indent=2))


if __name__ == "__main__":
    main()
