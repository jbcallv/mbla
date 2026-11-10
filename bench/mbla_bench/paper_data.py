"""data files for the final evaluation report's gnuplot figures (research/eval_paper/). read from the result tables."""

import json
import re
import sys
from pathlib import Path

import pandas as pd

TABLES = Path("results/tables")
PAIRS = {"qwen3-1.7b": "Qwen3-1.7B", "qwen3-4b": "Qwen3-4B", "qwen3-8b": "Qwen3-8B", "qwen3-reranker-0.6b": "Reranker-0.6B", "qwen3-reranker-8b": "Reranker-8B"}
OTHERS = {"gpt-oss-120b": "gpt-oss-120b", "qwen3-30b": "Qwen3-30B", "capmas-scores": "CAPMAS", "set-only": "Everything"}
REACH = {"qwen3-4b": "4B", "qwen3-8b": "8B", "qwen3-30b": "30B", "gpt-oss-120b": "gpt-oss", "capmas-scores": "CAPMAS"}
# label offsets (characters) so labels do not collide; default is right of the point
OFFSETS = {"Qwen3-4B": (-1, 1, "right"), "gpt-oss-120b": (1, 0.6, "left"), "Qwen3-30B": (1, -1.3, "left"), "Qwen3-1.7B": (1, 0.6, "left"),
           "Qwen3-8B": (1, -0.6, "left"), "Qwen3-4B tuned": (-0.5, -1.4, "right"), "Qwen3-8B tuned": (1, -2.6, "left"), "Everything": (-1, 0.8, "right")}


def estimates(experiment):
    frame = pd.read_csv(TABLES / experiment / "summary.csv")
    frame = frame[~frame["method"].str.contains("untuned")].copy()
    for column in ("coverage", "excess_C", "reach_A_injected", "reach_parent_injected"):
        frame[column] = frame[column].astype(str).str.split(" ").str[0].astype(float)
    frame["method"] = frame["method"].map(lambda method: re.sub(r"-s\d+$", "", method))
    return frame.groupby("method")[["coverage", "excess_C", "reach_A_injected", "reach_parent_injected"]].mean()


def labelled(label, x, y):
    dx, dy, align = OFFSETS.get(label, (1, 0, "left"))
    return f'"{label}" {x:.4f} {100 * y:.2f} {dx} {dy} {align}'


def tradeoff(out):
    plain, tuned, retrained = estimates("final"), estimates("final-tuned"), estimates("final-capmas-retrained")
    rows = {"plain": [], "tuned": [], "other": [], "arrows": []}
    for method, label in PAIRS.items():
        start, end = plain.loc[method], tuned.loc[f"{method}-tuned"]
        rows["plain"].append(labelled(label, start.excess_C, start.coverage))
        rows["tuned"].append(labelled(f"{label} tuned", end.excess_C, end.coverage))
        rows["arrows"].append(f"{start.excess_C:.4f} {100 * start.coverage:.2f} {end.excess_C - start.excess_C:.4f} {100 * (end.coverage - start.coverage):.2f}")
    for method, label in OTHERS.items():
        rows["other"].append(labelled(label, plain.loc[method].excess_C, plain.loc[method].coverage))
    bge = retrained.loc["capmas-retrained-bge-large"]
    rows["other"].append(labelled("CAPMAS retrained", bge.excess_C, bge.coverage))
    for name, lines in rows.items():
        (out / f"tradeoff_{name}.dat").write_text("\n".join(lines) + "\n")


def budget_rows(experiment):
    lines = (TABLES / experiment / "budget.md").read_text().splitlines()[2:]
    return [float(line.split("|")[3]) for line in lines if line.startswith("|")]


def budget(out):
    names = ["none", "0", "10", "30", "100", "300", "1000"]
    practice, final = budget_rows("dev-adaptive"), budget_rows("final-adaptive")
    lines = [f'{index} "{name}" {100 * a:.1f} {100 * b:.1f}' for index, (name, a, b) in enumerate(zip(names, practice, final))]
    (out / "budget.dat").write_text("# index label practice final\n" + "\n".join(lines) + "\n")


def reach(out):
    plain = estimates("final")
    lines = [f'"{label}" {100 * plain.loc[method].reach_A_injected:.1f} {100 * plain.loc[method].reach_parent_injected:.1f}' for method, label in REACH.items()]
    (out / "reach.dat").write_text("# helper backups-from-helper-list backups-from-everything\n" + "\n".join(lines) + "\n")


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "../research/eval_paper/data")
    out.mkdir(parents=True, exist_ok=True)
    tradeoff(out)
    budget(out)
    reach(out)
    rq_tables(out)
    (out / "sources.json").write_text(json.dumps({"tables": str(TABLES.resolve())}) + "\n")
    print(out)



# ---- tables answering RQ1-RQ5 (final methodology §3), written as LaTeX rows
PROMPTED = {"qwen3-4b": "Qwen3-4B (best)", "gpt-oss-120b": "gpt-oss-120b", "qwen3-8b": "Qwen3-8B", "qwen3-30b": "Qwen3-30B",
            "qwen3-1.7b": "Qwen3-1.7B", "qwen3-reranker-8b": "Reranker-8B", "qwen3-reranker-0.6b": "Reranker-0.6B",
            "capmas-scores": "CAPMAS", "capmas-retrained-bge-large": "CAPMAS retrained", "set-only": "Hand over everything"}
TRAINED = ["qwen3-1.7b", "qwen3-4b", "qwen3-8b", "qwen3-reranker-0.6b", "qwen3-reranker-8b"]


def per_task(experiment):
    frame = pd.read_csv(TABLES / experiment / "tasks.csv")
    frame = frame[~frame["method"].str.contains("untuned")].copy()
    frame["method"] = frame["method"].map(lambda method: re.sub(r"-s\d+$", "", method))
    return frame


def outcomes(group):
    return {"cov": group["covered_A-bounded_k3"].mean(), "cov_parent": group["covered_parent-bounded_k3"].mean(),
            "C": group["excess_C"].mean(), "plain": group["excess_plain"].mean(), "D": group["excess_D"].mean(),
            "rejected": group["rejected"].mean(), "refused": group["refused"].mean(),
            "reach": group["reach_A-bounded_k3"].mean(), "reach_parent": group["reach_parent-bounded_k3"].mean()}


def pct(value):
    return f"{100 * value:.0f}\\%"


def conditions(final, manifest, adaptive, method):
    rows = final[final["method"] == method]
    named = [("Clean", rows[rows["style"] == "none"]), ("Planted injection", rows[rows["style"] == "planted"]),
             ("Held-out injection styles", rows[~rows["style"].isin(["none", "planted"])])]
    named.append(("Inflated manifest", manifest[manifest["method"] == method]))
    if adaptive is not None:
        named.append(("Adaptive attacker, 1000 queries", adaptive[adaptive["method"] == method]))
    return [(name, outcomes(group)) for name, group in named if len(group)]


def write(out, name, lines):
    """table body; ends with the closing rule, since a rule after \\input inside a tabular breaks LaTeX."""
    (out / f"{name}.tex").write_text("\n".join(lines) + "\n\\bottomrule\n")


def rq_tables(out):
    final = pd.concat([per_task("final"), per_task("final-tuned"), per_task("final-capmas-retrained")])
    manifest = pd.concat([per_task(name) for name in ("final-manifest", "final-tuned-manifest", "final-capmas-retrained-manifest") if (TABLES / name / "tasks.csv").exists()])
    adaptive = per_task("final-adaptive")
    adaptive = adaptive[adaptive["item"].str.endswith("-q1000")]
    latency = pd.read_csv(TABLES / "latency" / "summary.csv").set_index("method")
    by_method = {method: outcomes(final[final["method"] == method]) for method in PROMPTED}
    write(out, "rq1", [f"{label} & {pct(r['cov'])} & {r['C']:.2f} & {r['plain']:.2f} & {r['D']:.2f} & {pct(r['rejected'])} \\\\" for label, r in ((PROMPTED[m], by_method[m]) for m in PROMPTED)])
    rq2 = []
    for method in PROMPTED:
        rows = final[final["method"] == method]
        clean, attacked = outcomes(rows[~rows["injected"]]), outcomes(rows[rows["injected"]])
        rq2.append(f"{PROMPTED[method]} & {pct(clean['reach'])} & {pct(clean['reach_parent'])} & {pct(attacked['reach'])} & {pct(attacked['reach_parent'])} & {pct(by_method[method]['cov'])} & {pct(by_method[method]['cov_parent'])} \\\\")
    write(out, "rq2", rq2)
    write(out, "rq3", [f"{name} & {pct(r['cov'])} & {r['C']:.2f} & {r['D']:.2f} & {pct(r['reach'])} & {pct(r['reach_parent'])} \\\\" for name, r in conditions(final, manifest, adaptive, "qwen3-4b")])
    rq4 = []
    for method, label in PROMPTED.items():
        if method in latency.index:
            rq4.append(f"{label} & {latency.loc[method, 'latency_p50_ms'] / 1000:.2f} & {latency.loc[method, 'latency_p95_ms'] / 1000:.2f} & {pct(by_method[method]['refused'])} \\\\")
    write(out, "rq4", rq4)
    rq5 = []
    for method in TRAINED:
        for suffix, label in (("", PROMPTED[method].replace(" (best)", "")), ("-tuned", "\\quad fine-tuned")):
            rows = final[final["method"] == method + suffix]
            whole, held = outcomes(rows), outcomes(rows[~rows["style"].isin(["none", "planted"])])
            rq5.append(f"{label} & {pct(whole['cov'])} & {whole['C']:.2f} & {pct(outcomes(rows[rows['injected']])['reach'])} & {pct(held['cov'])} & {held['C']:.2f} \\\\")
    write(out, "rq5", rq5)
    f5 = json.loads((TABLES / "heldout" / "f5.json").read_text())
    names = {**{f"{m}-tuned": f"{PROMPTED[m].replace(' (best)', '')} fine-tuned" for m in TRAINED}, **{m: PROMPTED[m].replace(" (best)", "") for m in TRAINED}}
    write(out, "f5", [f"{' vs.\\ '.join(names[part] for part in test['comparison'].split(' vs '))} & ${test['difference']:+.2f}$ & {test['coverage_difference'] * 100:+.0f} pts & {test['p_holm']:.3f} \\\\" for test in f5])


if __name__ == "__main__":
    main()
