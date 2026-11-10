"""data files for the final evaluation report's gnuplot figures (research/eval_paper/). read from the result tables."""

import json
import re
import sys
from pathlib import Path

import pandas as pd

TABLES = Path("results/tables")
PAIRS = {"qwen3-1.7b": "Qwen3-1.7B", "qwen3-4b": "Qwen3-4B", "qwen3-8b": "Qwen3-8B", "qwen3-reranker-0.6b": "Reranker-0.6B", "qwen3-reranker-8b": "Reranker-8B"}
OTHERS = {"gpt-oss-120b": "gpt-oss-120b", "qwen3-30b": "Qwen3-30B", "capmas-scores": "CAPMAS", "set-only": "Everything"}
REACH = {"qwen3-4b": "4B", "qwen3-8b": "8B", "qwen3-30b": "30B", "gpt-oss-120b": "120B", "capmas-scores": "CAPMAS"}
# label offsets (characters) so labels do not collide; default is right of the point
OFFSETS = {"Qwen3-4B": (-1, 1, "right"), "gpt-oss-120b": (1, 0.6, "left"), "Qwen3-30B": (1, -1.3, "left"), "Qwen3-1.7B": (1, 0.6, "left"),
           "Qwen3-8B": (1, -0.6, "left"), "Qwen3-4B tuned": (-0.5, -1.4, "right"), "Qwen3-8B tuned": (1, -1.6, "left"), "Everything": (-1, 0.8, "right")}


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
    (out / "sources.json").write_text(json.dumps({"tables": str(TABLES.resolve())}) + "\n")
    print(out)


if __name__ == "__main__":
    main()
