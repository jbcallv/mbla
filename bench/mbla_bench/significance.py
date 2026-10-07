import argparse
from pathlib import Path

import pandas as pd

from mbla_bench import data, report, stats

M1_METRICS = ["mac_C", "eac_C", "eac", "mac"]
M1_REFERENCE = "clm-zs"
CAP = 3


def per_item(frame, keys, columns):
    numeric = frame[keys + ["item", "template"] + columns].copy()
    for column in columns:
        numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
    return numeric.groupby(keys + ["item", "template"], as_index=False)[columns].mean()


def compare(first, second, metric, label):
    result = stats.paired_difference(first, second, metric)
    return {"comparison": label, "metric": metric, **result}


def with_holm(rows):
    frame = pd.DataFrame(rows)
    for metric, members in frame.groupby("metric"):
        frame.loc[members.index, "p_holm"] = stats.holm(members["p"].fillna(1.0).tolist())
    return frame


def m1_comparisons(quality):
    items = per_item(quality[quality["input"] == "full"], ["method"], M1_METRICS)
    reference = items[items["method"] == M1_REFERENCE]
    rows = []
    for method in sorted(set(items["method"]) - {M1_REFERENCE}):
        for metric in M1_METRICS:
            rows.append(compare(items[items["method"] == method], reference, metric, f"{method} - {M1_REFERENCE}"))
    return with_holm(rows)


def exact_match_tests(quality):
    items = per_item(quality[quality["input"] == "full"], ["method"], ["exact_match"])
    reference = items[items["method"] == M1_REFERENCE].set_index("item")["exact_match"] >= 0.5
    rows = []
    for method in sorted(set(items["method"]) - {M1_REFERENCE}):
        candidate = items[items["method"] == method].set_index("item")["exact_match"] >= 0.5
        shared = candidate.index.intersection(reference.index)
        p_value = stats.mcnemar_exact(candidate[shared].tolist(), reference[shared].tolist())
        rows.append(
            {
                "comparison": f"{method} - {M1_REFERENCE}",
                "metric": "exact_match",
                "difference": candidate[shared].mean() - reference[shared].mean(),
                "p": p_value,
            }
        )
    return with_holm(rows)


def m3_comparisons(recovery):
    capped = recovery[(recovery["cap"] == CAP) & (recovery["input"] == "full")]
    rows = []
    for method in sorted(capped["method"].unique()):
        modes = {
            mode: per_item(capped[(capped["method"] == method) & (capped["mode"] == mode)], ["method"], ["ras_recovery", "success"])
            for mode in ("admitted", "bound-only")
        }
        for metric in ("ras_recovery", "success"):
            rows.append(compare(modes["admitted"], modes["bound-only"], metric, f"{method}: admitted - bound-only"))
    return with_holm(rows)


def m4_comparisons(quality):
    items = per_item(quality, ["method", "input"], ["mac_C", "eac_C"])
    rows = []
    for method in sorted(items["method"].unique()):
        full = items[(items["method"] == method) & (items["input"] == "full")]
        for input_name in ("text", "args", "history"):
            reduced = items[(items["method"] == method) & (items["input"] == input_name)]
            for metric in ("mac_C", "eac_C"):
                rows.append(compare(reduced, full, metric, f"{method}: {input_name} - full"))
    return with_holm(rows)


SYSTEMS = {
    "mbla (qwen3-8b, admitted)": ("qwen3-8b", "admitted"),
    "capmas as published (no recovery)": ("capmas", "none"),
    "capmas scorer + mbla recovery": ("capmas-scores", "admitted"),
}
SYSTEM_PAIRS = [
    ("mbla (qwen3-8b, admitted)", "capmas as published (no recovery)"),
    ("mbla (qwen3-8b, admitted)", "capmas scorer + mbla recovery"),
    ("capmas scorer + mbla recovery", "capmas as published (no recovery)"),
]
SYSTEM_RECOVERY_METRICS = ["ras_recovery", "success"]
SYSTEM_QUALITY_METRICS = ["eac_C", "mac_C", "exact_match"]


def system_rows(quality, recovery, name):
    method, mode = SYSTEMS[name]
    chosen = recovery[
        (recovery["method"] == method) & (recovery["mode"] == mode) & (recovery["cap"] == CAP) & (recovery["input"] == "full")
    ]
    merged = per_item(chosen, ["method"], SYSTEM_RECOVERY_METRICS).merge(
        per_item(quality[(quality["method"] == method) & (quality["input"] == "full")], ["method"], SYSTEM_QUALITY_METRICS)[
            ["item"] + SYSTEM_QUALITY_METRICS
        ],
        on="item",
    )
    return merged


def system_comparisons(quality, recovery):
    available = set(quality["method"])
    rows = []
    for first, second in SYSTEM_PAIRS:
        if SYSTEMS[first][0] not in available or SYSTEMS[second][0] not in available:
            continue
        for metric in SYSTEM_RECOVERY_METRICS + SYSTEM_QUALITY_METRICS:
            rows.append(
                compare(system_rows(quality, recovery, first), system_rows(quality, recovery, second), metric, f"{first} - {second}")
            )
    return with_holm(rows) if rows else pd.DataFrame()


def write(frame, name):
    path = Path("results/tables") / name
    frame.to_csv(path.with_suffix(".csv"), index=False)
    path.with_suffix(".md").write_text(frame.to_markdown(index=False, floatfmt=".4f") + "\n")
    print(f"{path.with_suffix('.csv')}: {len(frame)} comparisons")


def frames_for(experiment, items):
    rows = data.load_predictions(Path("results/raw") / experiment)
    return report.metric_rows(rows, items), report.recovery_rows(rows, items)


def main():
    parser = argparse.ArgumentParser(
        description="paired, template-clustered significance tests for the pre-declared comparisons (spec 7.9)"
    )
    parser.add_argument("--items", default="data/tasks/test.jsonl")
    arguments = parser.parse_args()
    items = data.items_by_id(arguments.items)
    e1_quality, e1_recovery = frames_for("e1", items)
    write(m1_comparisons(e1_quality), "significance_m1_quality")
    write(exact_match_tests(e1_quality), "significance_m1_exact_match")
    write(m3_comparisons(e1_recovery), "significance_m3_recovery")
    write(m1_comparisons(frames_for("e4", items)[0]), "significance_m5_backbone")
    write(m4_comparisons(frames_for("e3", items)[0]), "significance_m4_inputs")
    write(system_comparisons(e1_quality, e1_recovery), "significance_capmas_systems")


if __name__ == "__main__":
    main()
