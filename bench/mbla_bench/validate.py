import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import yaml

from mbla_bench import answer, reference

REQUIRED_FIELDS = ["id", "template", "handoff", "split", "request", "parent", "ceiling", "plans", "attacks"]
STRUCTURAL = {"", "issues", "contents", "pulls", "releases", "actions", "doc", "folder", "~default"}


def load_items(task_dir):
    items = []
    for split_file in sorted(task_dir.glob("*.jsonl")):
        items += [json.loads(line) for line in split_file.read_text().splitlines() if line]
    return items


def named_in_text(named, text):
    service, _, resource = named.partition(":")
    segments = resource.split("/")[1:] if service == "slack" else resource.split("/")
    return all(segment in text for segment in segments if segment not in STRUCTURAL)


def item_problems(item, decoys):
    problems = [f"missing field {field}" for field in REQUIRED_FIELDS if field not in item]
    if problems:
        return problems
    parent = reference.parse_all(item["parent"])
    remote = item["request"]["receiver"]["remote"]
    every = item["parent"] + item["ceiling"] + item["request"]["manifest"] + [need for plan in item["plans"] for need in plan]
    if any(atom.kind == "X" for atom in reference.parse_all(every)):
        problems.append("executable permission")
    if remote and item["ceiling"]:
        problems.append("remote receiver with a non-empty ceiling")
    pool = answer.candidates(item)
    if remote and any(atom.kind == "D" for atom in pool):
        problems.append("volume candidate for a remote receiver")
    problems += [f"plain candidate {atom} is not a decoy" for atom in pool if atom.kind == "plain" and str(atom) not in decoys]
    actions = answer.universe(item)
    for index, plan in enumerate(item["plans"]):
        if not reference.within(reference.parse_all(plan), parent):
            problems.append(f"plan {index} exceeds parent")
        if answer.plan_candidates(plan, pool, actions) is None:
            problems.append(f"plan {index} not expressible in candidates")
    problems += [f"attack {attack['id']} not reachable under parent" for attack in item["attacks"] if not reference.within(reference.parse_all(attack["needs"]), parent)]
    problems += [f"named {named} not in task text" for named in item["request"]["named"] if not named_in_text(named, item["request"]["text"])]
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
        raise SystemExit("tasks are not frozen yet: review the answer keys, then run make freeze")
    recorded = dict(reversed(line.split("  ")) for line in (task_dir / "SHA256SUMS").read_text().splitlines())
    return [name for name, digest in checksums(task_dir).items() if recorded.get(name) != digest]


def main():
    parser = argparse.ArgumentParser(description="validate benchmark tasks and freeze or verify checksums")
    parser.add_argument("--tasks", default="data/tasks")
    parser.add_argument("--templates", default="data/templates")
    parser.add_argument("--freeze", action="store_true", help="write SHA256SUMS")
    parser.add_argument("--verify", action="store_true", help="fail if files differ from SHA256SUMS")
    arguments = parser.parse_args()
    task_dir = Path(arguments.tasks)
    decoys = set(yaml.safe_load((Path(arguments.templates) / "delegations.yaml").read_text())["decoys"])
    items = load_items(task_dir)
    problems = split_problems(items) + [f"{item.get('id')}: {problem}" for item in items for problem in item_problems(item, decoys)]
    for problem in problems:
        print(problem)
    if problems:
        raise SystemExit(f"{len(problems)} problems in {len(items)} tasks")
    if arguments.verify and frozen_mismatches(task_dir):
        raise SystemExit(f"changed since freeze: {frozen_mismatches(task_dir)}")
    if arguments.freeze:
        write_checksums(task_dir)
    print(f"{len(items)} tasks valid")


if __name__ == "__main__":
    main()
