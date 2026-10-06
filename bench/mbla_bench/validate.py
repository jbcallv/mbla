import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from mbla_bench import reference

REQUIRED_FIELDS = ["id", "template", "split", "request", "parent", "ceiling", "reference", "attacks"]


def load_items(task_dir):
    items = []
    for split_file in sorted(task_dir.glob("*.jsonl")):
        items += [json.loads(line) for line in split_file.read_text().splitlines() if line]
    return items


def item_problems(item):
    problems = [f"missing field {field}" for field in REQUIRED_FIELDS if field not in item]
    if problems:
        return problems
    parent = reference.parse_all(item["parent"])
    reference_policy = reference.parse_all(item["reference"])
    reference.parse_all(item["ceiling"] + item["request"]["manifest"])
    if not reference.within(reference_policy, parent):
        problems.append("reference exceeds parent")
    for attack in item["attacks"]:
        needs = reference.parse_all(attack["needs"])
        if not reference.within(needs, parent):
            problems.append(f"attack {attack['id']} not reachable under parent")
        if reference.within(needs, reference_policy):
            problems.append(f"attack {attack['id']} allowed by reference")
    return problems


def split_problems(items):
    splits_by_template = defaultdict(set)
    for item in items:
        splits_by_template[item["template"]].add(item["split"])
    leaks = [f"template {template} in splits {sorted(splits)}" for template, splits in splits_by_template.items() if len(splits) > 1]
    ids = [item["id"] for item in items]
    duplicates = [f"duplicate id {item_id}" for item_id in set(ids) if ids.count(item_id) > 1]
    return leaks + duplicates


def checksums(task_dir):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(task_dir.glob("*.jsonl"))}


def write_checksums(task_dir):
    lines = [f"{digest}  {name}" for name, digest in checksums(task_dir).items()]
    (task_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def frozen_mismatches(task_dir):
    if not (task_dir / "SHA256SUMS").exists():
        raise SystemExit("tasks are not frozen yet: audit the references, then run make freeze")
    recorded = dict(reversed(line.split("  ")) for line in (task_dir / "SHA256SUMS").read_text().splitlines())
    return [name for name, digest in checksums(task_dir).items() if recorded.get(name) != digest]


def main():
    parser = argparse.ArgumentParser(description="validate benchmark items and freeze or verify checksums")
    parser.add_argument("--tasks", default="data/tasks")
    parser.add_argument("--freeze", action="store_true", help="write SHA256SUMS")
    parser.add_argument("--verify", action="store_true", help="fail if files differ from SHA256SUMS")
    arguments = parser.parse_args()
    task_dir = Path(arguments.tasks)
    items = load_items(task_dir)
    problems = split_problems(items) + [f"{item.get('id')}: {problem}" for item in items for problem in item_problems(item)]
    for problem in problems:
        print(problem)
    if problems:
        raise SystemExit(f"{len(problems)} problems in {len(items)} items")
    if arguments.verify and frozen_mismatches(task_dir):
        raise SystemExit(f"changed since freeze: {frozen_mismatches(task_dir)}")
    if arguments.freeze:
        write_checksums(task_dir)
    print(f"{len(items)} items valid")


if __name__ == "__main__":
    main()
