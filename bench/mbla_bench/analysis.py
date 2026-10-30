"""analysis plan (final methodology §9): best helper chosen on development data, comparison families with Holm's
correction, sign-flip tests on per-template means, coverage non-inferiority with a 2-point margin."""

import argparse
import json
from pathlib import Path

import pandas as pd

from mbla_bench import data, stats, tune

PROMPTED = ("generative", "decision", "capmas")
MARGIN = 0.02
COVERAGE = "covered_A-bounded_k3"
REACH = {"A-bounded": "reach_A-bounded_k3", "parent-bounded": "reach_parent-bounded_k3"}
COIN_FLIPS = ["random-25", "random-50", "random-75"]
UNDER_OUR_RULES = "capmas-scores"


def per_task(experiment):
    frame = pd.read_csv(Path("results/tables") / experiment / "tasks.csv")
    keys = ["method", "item", "template", "handoff", "injected", "style"]
    return frame.groupby(keys, as_index=False).mean(numeric_only=True)


def eligible(frame, models, thresholds):
    """prompted helpers meeting the coverage target on development; a scorer whose cutoffs miss it is not eligible."""
    chosen = {}
    for method, group in frame.groupby("method"):
        if models.get(method, {}).get("paradigm") not in PROMPTED or "fixed_thresholds" in models.get(method, {}):
            continue
        if method in thresholds and not thresholds[method]["meets_target"]:
            continue
        coverage = group[COVERAGE].mean()
        if coverage >= tune.TARGET_COVERAGE:
            chosen[method] = {"coverage": coverage, "excess_C": group["excess_C"].mean()}
    return chosen


def best_helper(development, models, thresholds):
    candidates = eligible(development, models, thresholds)
    best = min(candidates, key=lambda method: candidates[method]["excess_C"]) if candidates else None
    return best, candidates


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


def families(final, best, manifest=None):
    planted = lambda rows: rows["style"] == "planted"
    held_out = lambda rows: rows["injected"] & (rows["style"] != "planted")
    attacks = [("planted", benefit_retained(final, best, planted)), ("held-out styles", benefit_retained(final, best, held_out))]
    if manifest is not None:
        attacks.append(("inflated manifest", benefit_retained(final, best, None, manifest)))
    return {
        "F1 (RQ1) best helper vs set-only, excess authority in C": with_holm([compare(final, best, "set-only", "excess_C")]),
        "F2 (RQ2) A-bounded vs parent-bounded recovery": with_holm([recovery_rules(final, best, False), recovery_rules(final, best, True)]),
        "F3 best helper vs CAPMAS under our rules and coin flips, excess authority in C": with_holm(
            [compare(final, best, other, "excess_C") for other in [UNDER_OUR_RULES] + COIN_FLIPS]
        ),
        "F4 (RQ3) benefit retained under attack vs clean": with_holm([dict(test, attack=name) for name, test in attacks if test]),
    }


def write_markdown(path, best, candidates, inferiority, tests):
    lines = [f"# Analysis ({path.parent.name})", "", f"Best helper, chosen on the development set: **{best}**", ""]
    lines += ["| Eligible helper | Development coverage | Development excess C |", "|---|---|---|"]
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
    parser.add_argument("--thresholds", default="results/thresholds.json")
    arguments = parser.parse_args()
    models = data.load_yaml("config/models.yaml")["methods"]
    thresholds = json.loads(Path(arguments.thresholds).read_text()) if Path(arguments.thresholds).exists() else {}
    best, candidates = best_helper(per_task(arguments.development), models, thresholds)
    out = Path("results/tables") / arguments.final / "analysis.md"
    if best is None:
        out.write_text(f"# Analysis ({arguments.final})\n\nNo prompted helper meets the coverage target on the development set yet.\n")
        print(out.read_text())
        return
    final = per_task(arguments.final)
    manifest_tasks = Path("results/tables") / f"{arguments.final}-manifest" / "tasks.csv"
    tests = families(final, best, per_task(f"{arguments.final}-manifest") if manifest_tasks.exists() else None)
    write_markdown(out, best, candidates, non_inferiority(final, best), tests)
    (out.with_suffix(".json")).write_text(json.dumps({"best": best, "candidates": candidates, "families": tests}, indent=2, default=float) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
