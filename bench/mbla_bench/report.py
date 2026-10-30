"""tables for one experiment under the final methodology (§8 metrics, §9 intervals). the pilot's report is at tag pilot-final."""

import argparse
from pathlib import Path

import pandas as pd

from mbla_bench import answer, data, metrics, simulate, stats

CAPS = [0, 1, 3, 5]
RECOVERY = ["A-bounded", "parent-bounded"]
MAIN_CAP = 3
UNTUNED = 0.5


def task_frame(items, rows, keys):
    records = []
    for row in rows:
        item = items[row["item"]]
        record = {
            "method": row["method"],
            "seed": row["seed"],
            "item": item["id"],
            "template": item["template"],
            "handoff": item["handoff"],
            "breadth": item["breadth"],
            "injected": item["variant"] == "injection",
            "style": item.get("injection_style") or "none",
            "remote": item["request"]["receiver"]["remote"],
            "latency_ms": row["latency_ms"],
            "hardware": row["hardware"],
        }
        record.update(metrics.item_metrics(item, row, required=keys[item["id"]]))
        for mode in RECOVERY:
            for cap in CAPS:
                outcome = simulate.simulate(item, row, mode, cap, required=keys[item["id"]])
                record[f"covered_{mode}_k{cap}"] = outcome["covered"]
                record[f"reach_{mode}_k{cap}"] = outcome["reach_recovery"]
        record.update({key: outcome[key] for key in ("refused", "rejected", "reach_delegation", "avoidable_goals", "unavoidable_goals")})
        records.append(record)
    return pd.DataFrame(records)


def seed_averaged(frame):
    """one row per method and task: chance and sampled helpers are averaged over their seeds first."""
    keys = ["method", "item", "template", "handoff", "breadth", "injected", "style", "remote"]
    values = [column for column in frame.columns if column not in keys + ["seed", "hardware"]]
    return frame.groupby(keys, as_index=False)[values].mean(numeric_only=True)


def with_interval(frame, column):
    estimate, low, high = stats.cluster_bootstrap_ci(frame.astype({column: float}), column, resamples=2000)
    return None if estimate is None else f"{estimate:.3f} [{low:.3f}, {high:.3f}]"


def mean_of(frame, column):
    values = frame[column].dropna()
    return round(float(values.mean()), 3) if len(values) else None


def summary(frame, raw):
    lines = []
    for method, group in frame.groupby("method"):
        latency = raw[raw["method"] == method]["latency_ms"]
        lines.append({
            "method": method,
            "refused": mean_of(group, "refused"),
            "rejected": mean_of(group, "rejected"),
            "coverage": with_interval(group, f"covered_A-bounded_k{MAIN_CAP}"),
            "excess_C": with_interval(group, "excess_C"),
            "excess_plain": mean_of(group, "excess_plain"),
            "excess_D": mean_of(group, "excess_D"),
            "missing_C": mean_of(group, "missing_C"),
            "decoy_rate": mean_of(group, "decoy"),
            "reach_delegation": mean_of(group, "reach_delegation"),
            "reach_A_clean": mean_of(group[~group["injected"]], f"reach_A-bounded_k{MAIN_CAP}"),
            "reach_A_injected": mean_of(group[group["injected"]], f"reach_A-bounded_k{MAIN_CAP}"),
            "reach_parent_clean": mean_of(group[~group["injected"]], f"reach_parent-bounded_k{MAIN_CAP}"),
            "reach_parent_injected": mean_of(group[group["injected"]], f"reach_parent-bounded_k{MAIN_CAP}"),
            "latency_p50_ms": round(float(latency.median()), 1),
            "latency_p95_ms": round(float(latency.quantile(0.95)), 1),
        })
    return pd.DataFrame(lines)


def by_group(frame, group):
    columns = {"coverage": f"covered_A-bounded_k{MAIN_CAP}", "excess_C": "excess_C", "reach_A": f"reach_A-bounded_k{MAIN_CAP}", "rejected": "rejected"}
    return frame.groupby(["method", group]).agg(**{name: (column, "mean") for name, column in columns.items()}).round(3).reset_index()


def cap_sensitivity(frame):
    lines = []
    for method, group in frame.groupby("method"):
        for cap in CAPS:
            line = {"method": method, "k": cap}
            for mode in RECOVERY:
                line[f"coverage_{mode}"] = mean_of(group, f"covered_{mode}_k{cap}")
                line[f"reach_{mode}"] = mean_of(group, f"reach_{mode}_k{cap}")
            lines.append(line)
    return pd.DataFrame(lines)


def undefined_counts(frame):
    columns = [column for column in frame.columns if column.startswith(("excess_", "missing_")) or column == f"reach_A-bounded_k{MAIN_CAP}"]
    first = frame[frame["method"] == frame["method"].iloc[0]]
    return pd.DataFrame([{"metric": column, "undefined_tasks": int(first[column].isna().sum()), "tasks": len(first)} for column in columns])


def untuned_rows(rows, models):
    """per-candidate scorers without tuning: required if s >= 0.5, no plausible tier (final methodology §4)."""
    scorers = {name for name, method in models.items() if method.get("paradigm") in ("decision", "capmas") and "fixed_thresholds" not in method}
    return [dict(simulate.with_thresholds(row, UNTUNED, UNTUNED), method=row["method"] + " (untuned)") for row in rows if row["method"] in scorers]


def write_table(table, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path.with_suffix(".csv"), index=False)
    path.with_suffix(".md").write_text(table.to_markdown(index=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="tables for one experiment")
    parser.add_argument("experiment")
    parser.add_argument("--items", default=None)
    arguments = parser.parse_args()
    settings, models = data.load_yaml("config/experiments.yaml"), data.load_yaml("config/models.yaml")["methods"]
    experiment = settings["experiments"][arguments.experiment]
    items = data.items_by_id(arguments.items or experiment.get("items") or settings["items"][experiment["split"]])
    rows = data.load_predictions(Path("results/raw") / arguments.experiment)
    inconsistent = [row["item"] for row in rows if not simulate.thresholds_consistent(row)]
    if inconsistent:
        raise SystemExit(f"{len(inconsistent)} rows do not match their recorded cutoffs")
    rows += untuned_rows(rows, models)
    keys = {item_id: answer.tiers(item)[0] for item_id, item in items.items()}
    raw = task_frame(items, rows, keys)
    frame = seed_averaged(raw)
    tables = Path("results/tables") / arguments.experiment
    tables.mkdir(parents=True, exist_ok=True)
    raw.to_csv(tables / "tasks.csv", index=False)
    write_table(summary(frame, raw), tables / "summary")
    write_table(by_group(frame, "handoff"), tables / "by_handoff")
    write_table(by_group(frame, "breadth"), tables / "by_breadth")
    write_table(by_group(frame, "style"), tables / "by_injection_style")
    write_table(cap_sensitivity(frame), tables / "cap_sensitivity")
    write_table(undefined_counts(frame), tables / "undefined")
    print((tables / "summary.md").read_text())


if __name__ == "__main__":
    main()
