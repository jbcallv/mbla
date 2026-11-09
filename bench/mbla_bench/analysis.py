"""analysis plan (final methodology §9): best helper chosen on development data, comparison families with Holm's
correction, sign-flip tests on per-template means, coverage non-inferiority with a 2-point margin."""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from mbla_bench import data, stats

PROMPTED = ("generative", "decision", "capmas")
MARGIN = 0.02
COVERAGE = "covered_A-bounded_k3"
REACH = {"A-bounded": "reach_A-bounded_k3", "parent-bounded": "reach_parent-bounded_k3"}
COIN_FLIPS = ["random-25", "random-50", "random-75"]
UNDER_OUR_RULES = "capmas-scores"
RETRAINED = "capmas-retrained-bge-large"
ADAPTIVE_BUDGET = 1000


def per_task(experiment):
    frame = pd.read_csv(Path("results/tables") / experiment / "tasks.csv")
    keys = ["method", "item", "template", "handoff", "injected", "style"]
    return frame.groupby(keys, as_index=False).mean(numeric_only=True)


def seeds_merged(frame):
    """trained helpers as the mean of their seeds per task; untuned scorer rows left out."""
    frame = frame[~frame["method"].str.contains("untuned")].copy()
    frame["method"] = frame["method"].map(lambda method: re.sub(r"-s\d+$", "", method))
    keys = ["method", "item", "template", "handoff", "injected", "style"]
    return frame.groupby(keys, as_index=False).mean(numeric_only=True)


def eligible(frame, models):
    """prompted helpers within the margin of set-only's development coverage (D-54)."""
    floor = frame.loc[frame["method"] == "set-only", COVERAGE].mean() - MARGIN
    chosen = {}
    for method, group in frame.groupby("method"):
        if models.get(method, {}).get("paradigm") not in PROMPTED or "fixed_thresholds" in models.get(method, {}):
            continue
        if group[COVERAGE].mean() >= floor:
            chosen[method] = {"coverage": group[COVERAGE].mean(), "excess_C": group["excess_C"].mean()}
    return chosen


def best_helper(development, models):
    """helpers ranked by development excess in C, lowest first; the top one is the recommended setting."""
    candidates = eligible(development, models)
    ranked = dict(sorted(candidates.items(), key=lambda pair: pair[1]["excess_C"]))
    return next(iter(ranked), None), ranked


def compare(frame, first, second, column, subset=None):
    a, b = frame[frame["method"] == first], frame[frame["method"] == second]
    if subset is not None:
        a, b = a[subset(a)], b[subset(b)]
    differences = stats.template_differences(a, b, column)
    if len(differences) == 0:
        return None
    return {"comparison": f"{first} vs {second}", "metric": column, "templates": len(differences), "difference": float(differences.mean()), "p": stats.sign_flip_test(differences)}


def recovery_rules(frame, method, injected):
    rows = frame[(frame["method"] == method) & (frame["injected"] == injected)]
    differences = stats.template_differences(rows.assign(value=rows[REACH["A-bounded"]]), rows.assign(value=rows[REACH["parent-bounded"]]), "value")
    if len(differences) == 0:
        return None
    label = "injected" if injected else "clean"
    return {"comparison": f"{method}: A-bounded vs parent-bounded ({label})", "metric": "attack reachability", "templates": len(differences), "difference": float(differences.mean()), "p": stats.sign_flip_test(differences)}


def benefit_retained(frame, method, attacked, attack_frame=None):
    rows = frame[frame["method"] == method]
    clean = rows[~rows["injected"]]
    under_attack = rows[attacked(rows)] if attack_frame is None else attack_frame[attack_frame["method"] == method]
    if under_attack.empty:
        return None
    by_template = pd.DataFrame({"clean": clean.groupby("template")["excess_C"].mean(), "attack": under_attack.groupby("template")["excess_C"].mean()}).dropna()
    differences = (by_template["clean"] - by_template["attack"]).to_numpy()
    e_clean, e_attack = clean["excess_C"].mean(), under_attack["excess_C"].mean()
    retained = (1 - e_attack) / (1 - e_clean) if e_clean < 1 else None
    return {"comparison": "clean vs attacked", "metric": "excess_C", "templates": len(differences), "difference": float(differences.mean()), "retained": retained, "p": stats.sign_flip_test(differences)}


def with_holm(tests):
    tests = [test for test in tests if test is not None]
    for test, adjusted in zip(tests, stats.holm([test["p"] for test in tests])):
        test["p_holm"] = adjusted
    return tests


def non_inferiority(frame, method, reference_method="set-only"):
    paired = stats.paired_difference(frame[frame["method"] == method], frame[frame["method"] == reference_method], COVERAGE, resamples=10000)
    return {"comparison": f"{method} vs {reference_method}", "coverage_difference": paired["difference"], "low": paired["low"], "high": paired["high"], "margin": -MARGIN, "preserves": paired["low"] is not None and paired["low"] > -MARGIN}


def by_budget(frame, method):
    """attack (c): goal reachability and excess in C at each query budget, descriptive (D-62)."""
    rows = frame[frame["method"] == method].assign(budget=lambda rows: rows["item"].str.extract(r"-q(\d+)$")[0].astype(int))
    return rows.groupby("budget")[[REACH["A-bounded"], "excess_C"]].mean().reset_index()


def families(final, best, manifest=None, adaptive=None):
    planted = lambda rows: rows["style"] == "planted"
    held_out = lambda rows: rows["injected"] & (rows["style"] != "planted")
    attacks = [("planted", benefit_retained(final, best, planted)), ("held-out styles", benefit_retained(final, best, held_out))]
    if manifest is not None:
        attacks.append(("inflated manifest", benefit_retained(final, best, None, manifest)))
    if adaptive is not None:
        attacks.append((f"adaptive, {ADAPTIVE_BUDGET} queries", benefit_retained(final, best, None, adaptive[adaptive["item"].str.endswith(f"-q{ADAPTIVE_BUDGET}")])))
    return {
        "F1 (RQ1) best helper vs set-only, excess authority in C": with_holm([compare(final, best, "set-only", "excess_C")]),
        "F2 (RQ2) A-bounded vs parent-bounded recovery": with_holm([recovery_rules(final, best, False), recovery_rules(final, best, True)]),
        "F3 best helper vs CAPMAS under our rules and coin flips, excess authority in C": with_holm(
            [compare(final, best, other, "excess_C") for other in [UNDER_OUR_RULES] + ([RETRAINED] if RETRAINED in set(final["method"]) else []) + COIN_FLIPS]
        ),
        "F4 (RQ3) benefit retained under attack vs clean": with_holm([dict(test, attack=name) for name, test in attacks if test]),
    }


def write_markdown(path, best, candidates, inferiority, tests):
    lines = [f"# Analysis ({path.parent.name})", "", f"Recommended setting, chosen on the development set: **{best}**", ""]
    lines += ["| Ranked helper | Development coverage | Development excess C |", "|---|---|---|"]
    lines += [f"| {method} | {values['coverage']:.3f} | {values['excess_C']:.3f} |" for method, values in sorted(candidates.items())]
    if inferiority:
        lines += ["", f"Coverage non-inferiority (margin 2 points): difference {inferiority['coverage_difference']:.3f} [{inferiority['low']:.3f}, {inferiority['high']:.3f}], preserves coverage: {inferiority['preserves']}"]
    for family, results in tests.items():
        lines += ["", f"## {family}", "", "| Comparison | Metric | Templates | Difference | p | p (Holm) |", "|---|---|---|---|---|---|"]
        lines += [f"| {test['comparison']}{' (' + test['attack'] + ')' if 'attack' in test else ''} | {test['metric']} | {test['templates']} | {test['difference']:.3f} | {test['p']:.4f} | {test['p_holm']:.4f} |" for test in results]
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="best helper and comparison families")
    parser.add_argument("--development", default="dev")
    parser.add_argument("--final", default="final")
    arguments = parser.parse_args()
    models = data.load_yaml("config/models.yaml")["methods"]
    best, candidates = best_helper(per_task(arguments.development), models)
    out = Path("results/tables") / arguments.final / "analysis.md"
    if best is None:
        out.write_text(f"# Analysis ({arguments.final})\n\nNo prompted helper preserves coverage against set-only on the development set yet.\n")
        print(out.read_text())
        return
    final = per_task(arguments.final)
    retrained = Path("results/tables") / f"{arguments.final}-capmas-retrained" / "tasks.csv"
    if retrained.exists():
        final = pd.concat([final, seeds_merged(per_task(f"{arguments.final}-capmas-retrained"))], ignore_index=True)
    optional = lambda name: per_task(name) if (Path("results/tables") / name / "tasks.csv").exists() else None
    adaptive = optional(f"{arguments.final}-adaptive")
    tests = families(final, best, optional(f"{arguments.final}-manifest"), adaptive)
    write_markdown(out, best, candidates, non_inferiority(final, best), tests)
    if adaptive is not None:
        curve = by_budget(adaptive, best)
        (out.parent.parent / f"{arguments.final}-adaptive" / "budget.md").write_text(curve.to_markdown(index=False) + "\n")
    (out.with_suffix(".json")).write_text(json.dumps({"best": best, "candidates": candidates, "families": tests}, indent=2, default=float) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
