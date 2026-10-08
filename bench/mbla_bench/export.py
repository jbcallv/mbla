import argparse
import json
import math
from pathlib import Path

import pandas as pd

from mbla_bench import data, metrics, simulate

TABLES = Path("results/tables")
CURVE_METHODS = ["qwen3-8b", "qwen3-32b-awq", "gpt-oss-120b", "qwen3-reranker-8b", "clm-zs", "laya"]
INPUT_METHODS = ["qwen3-8b", "qwen3-reranker-8b", "clm-zs", "laya"]
CURVE_GRID = [round(step * 0.05, 2) for step in range(21)]
CAP = 3


def paradigms():
    return {name: method.get("paradigm", "") for name, method in data.load_yaml("config/models.yaml")["methods"].items()}


def write_dat(path, header, rows):
    lines = ["# " + " ".join(header)] + [" ".join(format_value(value) for value in row) for row in rows]
    path.write_text("\n".join(lines) + "\n")
    print(f"{path}: {len(rows)} rows")


def format_value(value):
    if isinstance(value, float):
        return "NaN" if math.isnan(value) else f"{value:.4f}"
    return str(value)


def ci_bounds(text):
    low, high = text.strip("[]").split(",")
    return float(low), float(high)


def e5_latency():
    latency = {}
    for path in sorted(Path("results/raw/e5").glob("*.jsonl")):
        rows = data.read_jsonl(path)
        values = sorted(row["latency_ms"] for row in rows)
        latency[rows[0]["method"]] = (values[len(values) // 2], values[int(len(values) * 0.95)])
    return latency


SAME_MODEL_LATENCY = {"capmas": "capmas-scores"}


def quality_rows():
    quality = pd.read_csv(TABLES / "e1_quality.csv").set_index("method")
    latency, kinds = e5_latency(), paradigms()
    rows = []
    for method, entry in quality.sort_values("eac_C").iterrows():
        timed = method if method in latency else SAME_MODEL_LATENCY.get(method, method)
        p50, p95 = latency.get(timed, (float("nan"), float("nan")))
        rows.append(
            [method, kinds.get(method, ""), p50, p95, entry["eac_C"], entry["mac_C"], entry["exact_match"], entry["over_privileged"]]
        )
    return rows


def recovery_rows():
    recovery = pd.read_csv(TABLES / "e1_recovery.csv")
    capped = recovery[(recovery["cap"] == CAP) & (recovery["input"] == "full")]
    bound = capped[capped["mode"] == "bound-only"].set_index("method")
    admitted = capped[capped["mode"] == "admitted"].set_index("method")
    rows = []
    for method in admitted.sort_values("ras_recovery").index:
        low, high = ci_bounds(admitted.loc[method, "ras_recovery_ci"])
        rows.append(
            [method, bound.loc[method, "ras_recovery"], admitted.loc[method, "ras_recovery"], low, high, admitted.loc[method, "success"]]
        )
    return rows


def fortis_rows():
    task1 = {entry["method"]: entry for entry in json.loads((TABLES / "fortis1_fortis_metrics.json").read_text())}
    task2 = {entry["method"]: entry for entry in json.loads((TABLES / "fortis2_fortis_metrics.json").read_text())}
    order = sorted(task1, key=lambda method: -task1[method]["exact_match"])
    return [
        [
            method,
            task1[method]["exact_match"],
            task1[method]["over_privilege"],
            task2[method]["exact_match"],
            task2[method]["over_privilege"],
        ]
        for method in order
    ]


def input_rows():
    inputs = pd.read_csv(TABLES / "e3_quality.csv").pivot(index="method", columns="input", values="eac_C")
    return [
        [position, name, *(inputs.loc[method, name] for method in INPUT_METHODS)]
        for position, name in enumerate(["text", "args", "history", "full"])
    ]


def curve_rows(method, rows, items):
    method_rows = [row for row in rows if row["method"] == method and row["seed"] == 0]
    points = []
    for threshold in CURVE_GRID:
        scored = [metrics.item_metrics(items[row["item"]], simulate.with_thresholds(row, threshold, threshold)) for row in method_rows]
        eac = [entry["eac_C"] for entry in scored if entry["eac_C"] is not None]
        mac = [entry["mac_C"] for entry in scored if entry["mac_C"] is not None]
        points.append([threshold, sum(eac) / len(eac), sum(mac) / len(mac)])
    return points


def latex_table(path, header, rows):
    lines = ["\\begin{tabular}{l" + "r" * (len(header) - 1) + "}", "\\toprule", " & ".join(header) + " \\\\", "\\midrule"]
    lines += [" & ".join(latex_cell(value) for value in row) + " \\\\" for row in rows]
    lines += ["\\bottomrule", "\\end{tabular}"]
    path.write_text("\n".join(lines) + "\n")
    print(f"{path}: {len(rows)} rows")


def latex_cell(value):
    if not isinstance(value, float):
        return str(value).replace("_", "\\_")
    if math.isnan(value):
        return "--"
    return f"{value:.0f}" if value >= 10 else f"{value:.3f}"


KIND_NAMES = {"decision": "yes/no scorer", "generative": "LLM", "baseline": "simple rule", "bound": "no reduction", "capmas": "CAPMAS"}


def percent(value):
    return "--" if math.isnan(value) else f"{100 * value:.0f}\\%"


def milliseconds(value):
    return "instant" if math.isnan(value) else f"{value:,.0f}"


def plain_quality_rows(quality):
    return [
        [row[0], KIND_NAMES.get(row[1], row[1]), milliseconds(row[2]), percent(row[4]), percent(row[5]), percent(row[6])] for row in quality
    ]


def plain_recovery_rows():
    return [[row[0], percent(row[1]), percent(row[2]), percent(row[5])] for row in recovery_rows()]


def plain_fortis_rows():
    return [[row[0], *(percent(value) for value in row[1:])] for row in fortis_rows()]


def audit_rows():
    audit = json.loads((TABLES / "reference_audit_independent.json").read_text())
    pair = audit["pairs"]["alvi_vs_joseph"]
    return [
        ["Permission decisions labeled by each reviewer", str(audit["rows"])],
        ["Decisions where both reviewers agreed", percent(pair["percent_agreement"])],
        ["Agreement beyond chance (1 = perfect, 0 = chance)", f"{pair['cohen_kappa']:.2f}"],
        ["Disagreements settled together afterwards", str(audit["rows_to_resolve"])],
    ]


def main():
    parser = argparse.ArgumentParser(description="export result tables into gnuplot data files and LaTeX tables for plots/ and report/")
    parser.add_argument("--plots", default="../plots/data")
    parser.add_argument("--report", default="../report/generated")
    arguments = parser.parse_args()
    plots, report = Path(arguments.plots), Path(arguments.report)
    plots.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)
    quality = quality_rows()
    write_dat(
        plots / "quality_latency.dat", ["method", "paradigm", "p50_ms", "p95_ms", "eac_C", "mac_C", "exact", "over_privileged"], quality
    )
    write_dat(
        plots / "recovery.dat", ["method", "ras_bound_only", "ras_admitted", "ras_low", "ras_high", "success_admitted"], recovery_rows()
    )
    write_dat(plots / "fortis.dat", ["method", "t1_exact", "t1_over_privilege", "t2_exact", "t2_over_privilege"], fortis_rows())
    write_dat(plots / "inputs.dat", ["position", "input", *INPUT_METHODS], input_rows())
    items, rows = data.items_by_id("data/tasks/test.jsonl"), data.load_predictions("results/raw/e1")
    for method in CURVE_METHODS:
        write_dat(plots / f"curve_{method}.dat", ["threshold", "eac_C", "mac_C"], curve_rows(method, rows, items))
    latex_table(
        report / "quality.tex",
        ["Model", "Kind", "Time (ms)", "Extra granted", "Needed but missed", "Exactly right"],
        plain_quality_rows(quality),
    )
    latex_table(report / "recovery.tex", ["Model", "Paper's rule", "Our rule", "Normal tasks finished"], plain_recovery_rows())
    latex_table(report / "fortis.tex", ["Model", "Right skill", "Riskier skill", "Right tools", "Extra tools"], plain_fortis_rows())
    latex_table(report / "audit.tex", ["Human check of the answer key", ""], audit_rows())


if __name__ == "__main__":
    main()
