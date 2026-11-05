"""settles two writer fields the human check found unreliable: the check step and the second plan (D-48)."""
import json
import re
from pathlib import Path

from mbla_bench import data
from mbla_bench.synth.run import SIZES

CONDITION = re.compile(r"(?<!verify )(?<!check )(?<!see )(?<!determine )\bif\b|\bunless\b", re.I)
READING = re.compile(r"read|get|list|history")


def real_text(item):
    planted = [attack["injection"] for attack in item["attacks"] if attack["id"] == item["injected_attack"]]
    return item["request"]["text"].replace(planted[0], "") if planted else item["request"]["text"]


def only_reads(permission):
    return permission.startswith(("fs:", "net:")) or bool(READING.search(permission.split(":")[1]))


def one_plan(plans):
    """the writer's plan, or its second plan when the only difference is a folder the task does not need."""
    plan = plans[0]
    for other in plans[1:]:
        dropped = set(plan) - set(other)
        if dropped and set(other) < set(plan) and all(need.startswith("fs:") for need in dropped):
            plan = other
    return plan


def settled(item):
    plan = one_plan(item["plans"])
    kept = {key: value for key, value in item.items() if key != "check"}
    reads = [need for need in plan if only_reads(need)]
    check = item.get("check") or (reads if len(reads) < len(plan) else None)
    return {**kept, "plans": [plan], **({"check": check} if check and CONDITION.search(real_text(item)) else {})}


def main():
    for split in SIZES:
        path = Path(f"data/tasks/synth_{split}.jsonl")
        items = [settled(item) for item in data.read_jsonl(path)]
        path.write_text("".join(json.dumps(item) + "\n" for item in items))
        print(split, len(items))


if __name__ == "__main__":
    main()
