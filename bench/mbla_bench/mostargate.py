"""mostargate external test (final methodology §5): its 100 test prompts, the 15 permissions of its taxonomy as
candidates, graded by its own metrics code. the helper's proposal is the grant. evaluation only; GPL-3.0, so neither
its code nor its data is copied into this repository."""

import argparse
import json
import sys
from pathlib import Path

from mbla_bench import data

REPOSITORY = "https://github.com/0xballistics/mostargate"
PINNED_COMMIT = "0518a1f7811ca929b5b17d550017a84e184185b6"
SOURCE = Path("data/external/mostargate-src").resolve()
OUTPUT = Path("data/external/mostargate")


def official():
    """their constants and metrics, imported from the pinned checkout."""
    sys.path.insert(0, str(SOURCE))
    from mostargate import constants
    from mostargate.experiments import metrics

    return constants, metrics


def permission(tool):
    return f"mostargate:{tool}:tool"


def item(record, tools):
    return {
        "id": record["id"],
        "template": record["department"],
        "handoff": "mostargate",
        "split": "external",
        "request": {
            "protocol": "mostargate",
            "operation": "scope",
            "receiver": {"name": "enterprise-agent", "remote": False},
            "text": record["prompt"],
            "history": [],
            "manifest": [],
            "named": [],
        },
        "parent": [permission(tool) for tool in tools],
        "ceiling": [],
        "plans": [[permission(tool) for tool in tools if record["permissions"].get(tool)]],
        "attacks": [],
        "mostargate": {"department": record["department"], "sensitivity": record["sensitivity"]},
    }


def build():
    constants, _ = official()
    records = json.loads((SOURCE / "dataset/test.json").read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "test.jsonl").write_text("".join(json.dumps(item(record, constants.TOOLS)) + "\n" for record in records))
    operations = [{"service": "mostargate", "operation": tool, "description": description} for tool, description in constants.TOOLS.items()]
    (OUTPUT / "universe.json").write_text(json.dumps({"version": 1, "source": f"{REPOSITORY}@{PINNED_COMMIT}", "operations": operations}, indent=2) + "\n")
    print(f"{OUTPUT / 'test.jsonl'}: {len(records)} items")


def report(experiment):
    constants, metrics = official()
    records = {record["id"]: record for record in json.loads((SOURCE / "dataset/test.json").read_text())}
    by_method = {}
    for row in data.load_predictions(Path("results/raw") / experiment):
        granted = {name.split(":")[1] for name in row["initial"]}
        by_method.setdefault(row["method"], {})[row["item"]] = metrics.evaluate(records[row["item"]], granted)
    baselines = {"c0 (all 15)": set(constants.TOOLS), "c1 (role ceiling)": None}
    for name, granted in baselines.items():
        by_method[name] = {key: metrics.evaluate(record, granted if granted is not None else constants.DEPARTMENT_CEILINGS[record["department"]]) for key, record in records.items()}
    summary = {method: metrics.summarise(list(results.values())) for method, results in sorted(by_method.items())}
    out = Path("results/tables") / f"{experiment}_metrics.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    for method, entry in summary.items():
        print(f"{method:28} n={entry['n_records']:3} delta={entry['mean_raw_delta']:.2f} sev={entry['mean_severity_weighted_delta']:.2f} over={entry['overshoot_rate']:.2f} under={entry['undershoot_rate']:.2f} macroF1={entry['macro_f1']:.3f}")


def main():
    parser = argparse.ArgumentParser(description="mostargate external test, graded by its own metrics")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build")
    commands.add_parser("report").add_argument("experiment")
    arguments = parser.parse_args()
    build() if arguments.command == "build" else report(arguments.experiment)


if __name__ == "__main__":
    main()
