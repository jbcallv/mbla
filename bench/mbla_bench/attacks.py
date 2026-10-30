"""attack variants derived from a task file (final methodology §5, attacks (d)); derived deterministically, so freezing
the source file freezes them too."""

import argparse
import json
import re
from pathlib import Path

from mbla_bench import answer, data


def target(item, required):
    """the goal an operator would slip into the manifest, chosen by name binding among the avoidable goals."""
    avoidable = [attack for attack in item["attacks"] if not answer.unavoidable(item, attack, required)]
    if not avoidable:
        return None
    binding = int(re.search(r"-b(\d+)-", item["id"]).group(1))
    return avoidable[binding % len(avoidable)]


def inflated_manifest(item):
    """attack (d) on a task without an injected instruction, so its effect is the manifest's alone."""
    if item["variant"] != "benign":
        return None
    goal = target(item, answer.tiers(item)[0])
    if goal is None:
        return None
    request = dict(item["request"], manifest=list(dict.fromkeys(item["request"]["manifest"] + goal["needs"])))
    return dict(item, id=item["id"] + "-manifest", request=request, manifest_attack=goal["id"])


def main():
    parser = argparse.ArgumentParser(description="derive attack variants from a task file")
    parser.add_argument("--items", default="data/tasks/dev.jsonl")
    parser.add_argument("--out", default="data/attacks/dev_manifest.jsonl")
    arguments = parser.parse_args()
    variants = [variant for variant in map(inflated_manifest, data.read_jsonl(arguments.items)) if variant]
    Path(arguments.out).parent.mkdir(parents=True, exist_ok=True)
    Path(arguments.out).write_text("".join(json.dumps(variant) + "\n" for variant in variants))
    print(f"{arguments.out}: {len(variants)} tasks with an inflated manifest")


if __name__ == "__main__":
    main()
