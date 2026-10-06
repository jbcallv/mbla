import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mbla_bench import data, metrics, simulate, stats

CAPS = [1, 3, 5]
SUMMARY_COLUMNS = [
    "eac_C",
    "mac_C",
    "eac_N",
    "mac_N",
    "eac_F",
    "mac_F",
    "eac_X",
    "mac_X",
    "exact_match",
    "over_privileged",
    "no_action",
    "size",
]
RECOVERY_COLUMNS = ["success", "recoveries", "ras_initial", "ras_recovery"]
CURVE_GRID = [round(step * 0.05, 2) for step in range(21)]


def check_rows(rows):
    inconsistent = [row["item"] for row in rows if not simulate.thresholds_consistent(row)]
    if inconsistent:
        raise SystemExit(f"go and python threshold selection disagree on {len(inconsistent)} rows, e.g. {inconsistent[:3]}")


def metric_rows(rows, items):
    records = []
    for row in rows:
        item = items[row["item"]]
        base = {
            "item": row["item"],
            "template": item["template"],
            "variant": item["variant"],
            "method": row["method"],
            "input": row["input"],
            "seed": row["seed"],
        }
        base.update(metrics.item_metrics(item, row))
        base.update(
            {"latency_ms": row["latency_ms"], "input_tokens": row["input_tokens"], "failed": bool(row["error"]) or row["parse_failed"]}
        )
        records.append(base)
    return pd.DataFrame(records)


def recovery_rows(rows, items):
    records = []
    for row in rows:
        item = items[row["item"]]
        for mode in simulate.MODES:
            for cap in CAPS:
                outcome = simulate.simulate(item, row, mode, cap)
                records.append(
                    {
                        "item": row["item"],
                        "template": item["template"],
                        "method": row["method"],
                        "input": row["input"],
                        "seed": row["seed"],
                        **outcome,
                    }
                )
    return pd.DataFrame(records)


def averaged_over_seeds(frame, keys, columns):
    numeric = frame[keys + ["template"] + columns].copy()
    for column in columns:
        numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
    return numeric.groupby(keys + ["template"], as_index=False)[columns].mean()


def summarize(frame, group_keys, columns):
    summary = []
    per_item = averaged_over_seeds(frame, group_keys + ["item"], columns)
    for group, members in per_item.groupby(group_keys):
        entry = dict(zip(group_keys, group if isinstance(group, tuple) else (group,)))
        for column in columns:
            estimate, low, high = stats.cluster_bootstrap_ci(members, column)
            entry[column] = estimate
            entry[f"{column}_ci"] = f"[{low:.3f}, {high:.3f}]" if low is not None else ""
        entry["items"] = members["item"].nunique()
        summary.append(entry)
    return pd.DataFrame(summary)


def latency_table(frame, models):
    table = frame.groupby("method")["latency_ms"].describe(percentiles=[0.5, 0.95, 0.99])[["count", "50%", "95%", "99%"]]
    prices = {name: method.get("price_per_mtok_input", 0.0) for name, method in models["methods"].items()}
    tokens = frame.groupby("method")["input_tokens"].mean()
    table["usd_per_1k_delegations"] = [tokens[method] * prices.get(method, 0.0) / 1e6 * 1000 for method in table.index]
    table["failure_rate"] = frame.groupby("method")["failed"].mean()
    return table.reset_index()


def operating_curve(rows, items, method):
    method_rows = [row for row in rows if row["method"] == method and row["input"] == "full"]
    points = []
    for threshold in CURVE_GRID:
        scored = [metrics.item_metrics(items[row["item"]], simulate.with_thresholds(row, threshold, threshold)) for row in method_rows]
        points.append((threshold, mean_of(scored, "eac_C"), mean_of(scored, "mac_C")))
    return points


def mean_of(records, key):
    values = [record[key] for record in records if record[key] is not None]
    return float(np.mean(values)) if values else float("nan")


def plot_curves(rows, items, methods, path):
    figure, axis = plt.subplots(figsize=(5, 4))
    for method in methods:
        points = operating_curve(rows, items, method)
        axis.plot([point[1] for point in points], [point[2] for point in points], marker=".", label=method)
    axis.set_xlabel("capability excess authority (EAC)")
    axis.set_ylabel("capability missing authority (MAC)")
    axis.legend(fontsize=7)
    figure.tight_layout()
    figure.savefig(path)


def write_table(frame, path):
    frame.to_csv(path.with_suffix(".csv"), index=False)
    path.with_suffix(".md").write_text(frame.to_markdown(index=False, floatfmt=".3f") + "\n")


def main():
    parser = argparse.ArgumentParser(description="tables and figures for one experiment")
    parser.add_argument("experiment")
    parser.add_argument("--items", default="data/tasks/test.jsonl")
    arguments = parser.parse_args()
    items = data.items_by_id(arguments.items)
    rows = data.load_predictions(Path("results/raw") / arguments.experiment)
    check_rows(rows)
    models = data.load_yaml("config/models.yaml")
    tables, figures = Path("results/tables"), Path("results/figures")
    quality = metric_rows(rows, items)
    recovery = recovery_rows(rows, items)
    write_table(summarize(quality, ["method", "input"], SUMMARY_COLUMNS), tables / f"{arguments.experiment}_quality")
    write_table(summarize(quality, ["method", "input", "variant"], ["eac", "mac"]), tables / f"{arguments.experiment}_by_variant")
    write_table(summarize(recovery, ["method", "input", "mode", "cap"], RECOVERY_COLUMNS), tables / f"{arguments.experiment}_recovery")
    write_table(latency_table(quality, models), tables / f"{arguments.experiment}_latency")
    plot_curves(rows, items, sorted(quality["method"].unique()), figures / f"{arguments.experiment}_operating_curves.pdf")
    print(json.dumps({"rows": len(rows), "methods": sorted(quality["method"].unique())}))


if __name__ == "__main__":
    main()
