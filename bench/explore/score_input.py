"""exploratory only: scores results/explore/input runs on the development set, on unreviewed answer keys."""
import json
import sys
from pathlib import Path

import pandas as pd

from mbla_bench import answer, data, report

COVERED = "covered_A-bounded_k3"
REACH = "reach_A-bounded_k3"


def needs_folder(item):
    return any(text.startswith("fs:") for text in item["plans"][0])


def scored(path, items, keys):
    rows = data.read_jsonl(path)
    frame = report.task_frame(items, rows, keys)
    frame["folder_task"] = [needs_folder(items[item]) for item in frame["item"]]
    return frame


def row_for(name, frame):
    injected = frame[frame["injected"]]
    return {
        "input": name,
        "coverage": frame[COVERED].mean(),
        "coverage_folder_tasks": frame[frame["folder_task"]][COVERED].mean(),
        "coverage_other_tasks": frame[~frame["folder_task"]][COVERED].mean(),
        "excess_C": frame["excess_C"].mean(),
        "excess_D": frame["excess_D"].mean() if "excess_D" in frame else None,
        "decoy": frame["decoy"].mean(),
        "reach_injected": injected[REACH].mean(),
        "latency_p50": frame["latency_ms"].median(),
    }


def main():
    items = data.items_by_id("data/tasks/dev.jsonl")
    keys = {item_id: answer.tiers(item)[0] for item_id, item in items.items()}
    for method in sys.argv[1:]:
        table = [row_for(path.stem.split("__")[1], scored(path, items, keys)) for path in sorted(Path("results/explore/input").glob(f"{method}__*.jsonl"))]
        print(method)
        print(pd.DataFrame(table).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
