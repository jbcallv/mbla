import argparse
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

from mbla_bench import data

MODELS = "config/models.yaml"
EXPERIMENTS = "config/experiments.yaml"
DEFAULT_THRESHOLDS = {"initial": 0.8, "admit": 0.2}


def config_hash():
    digest = hashlib.sha256()
    for path in (MODELS, EXPERIMENTS):
        digest.update(Path(path).read_bytes())
    return digest.hexdigest()[:12]


def thresholds_for(method_name, method):
    if "fixed_thresholds" in method:
        return method["fixed_thresholds"]
    chosen_path = Path("results/thresholds.json")
    chosen = json.loads(chosen_path.read_text()) if chosen_path.exists() else {}
    return chosen.get(method_name, DEFAULT_THRESHOLDS)


def bench_command(settings, method_name, method, items_path, glossary, input_name, seed, output_path):
    thresholds = thresholds_for(method_name, method)
    flags = {
        "-items": items_path,
        "-out": output_path,
        "-method": method_name,
        "-scorer": method["scorer"],
        "-input": input_name,
        "-seed": seed,
        "-initial": thresholds["initial"],
        "-admit": thresholds["admit"],
        "-glossary": glossary,
        "-hardware": method.get("hardware", settings["hardware"]),
        "-warmup": settings["warmup"],
        "-endpoint": method.get("endpoint"),
        "-model": method.get("model"),
        "-extra": json.dumps(method["extra"]) if method.get("extra") else None,
    }
    command = [settings["mbla"], "bench"]
    for flag, value in flags.items():
        if value is not None:
            command += [flag, str(value)]
    return command


def planned_runs(settings, models, experiment_name, only_methods):
    experiment = settings["experiments"][experiment_name]
    methods = only_methods or experiment["methods"]
    for method_name in methods:
        method = models["methods"][method_name]
        for input_name in experiment["inputs"]:
            for seed in experiment.get("seeds", method.get("seeds", [0])):
                output_path = Path("results/raw") / experiment_name / f"{method_name}__{input_name}__s{seed}.jsonl"
                items_path = experiment.get("items") or settings["items"][experiment["split"]]
                glossary = experiment.get("glossary", settings["glossary"])
                yield output_path, bench_command(settings, method_name, method, items_path, glossary, input_name, seed, output_path)


def log_run(experiment_name, command, output_path):
    stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    line = f"| {stamp} | {experiment_name} | {output_path} | {config_hash()} | `{' '.join(command)}` |\n"
    with open("results/runs.md", "a") as log:
        log.write(line)


def line_count(path):
    with open(path) as lines:
        return sum(1 for _ in lines)


def already_complete(output_path, command):
    items_path = command[command.index("-items") + 1]
    return output_path.exists() and line_count(output_path) == line_count(items_path)


def execute(experiment_name, runs, dry_run):
    for output_path, command in runs:
        if already_complete(output_path, command):
            print(f"skip complete {output_path}")
            continue
        print(" ".join(command))
        if dry_run:
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, check=True, env=os.environ)
        log_run(experiment_name, command, output_path)


def main():
    parser = argparse.ArgumentParser(description="run one experiment from config/experiments.yaml through the Go mbla bench command")
    parser.add_argument("experiment")
    parser.add_argument("--methods", default="", help="comma-separated subset of methods")
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    settings, models = data.load_yaml(EXPERIMENTS), data.load_yaml(MODELS)
    only_methods = [name for name in arguments.methods.split(",") if name]
    execute(arguments.experiment, list(planned_runs(settings, models, arguments.experiment, only_methods)), arguments.dry_run)


if __name__ == "__main__":
    main()
