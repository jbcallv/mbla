import argparse
import json
import random
import subprocess
import tempfile
from pathlib import Path

from mbla_bench import reference

SERVICES = ["github", "fs"]
OPERATIONS = ["read", "write", "*"]
RESOURCES = ["a", "a/b", "a/b/c", "a/b#1", "a/b#12", "a/bc", "a*", "a/*", "a/b*", "*", "c", "c/d"]
QUALIFIERS = ["", "", "", "label=x", "label=y"]
NARROWINGS = ["/n", "#7", "/n/m"]


def random_atom(rng):
    return reference.Atom(rng.choice(SERVICES), rng.choice(OPERATIONS), rng.choice(RESOURCES), rng.choice(QUALIFIERS))


def random_policy(rng, size):
    return list({random_atom(rng) for _ in range(size)})


def narrowed(rng, atom):
    resource = atom.resource[:-1] + "x" if atom.resource.endswith("*") else atom.resource + rng.choice(NARROWINGS)
    operation = rng.choice(["read", "write"]) if atom.operation == "*" else atom.operation
    qualifier = atom.qualifier or rng.choice(QUALIFIERS)
    return reference.Atom(atom.service, operation, resource, qualifier)


def child_of(rng, parent, widen_probability):
    child = [narrowed(rng, atom) if rng.random() < 0.5 else atom for atom in parent if rng.random() < 0.7]
    if rng.random() < widen_probability:
        child.append(random_atom(rng))
    return child


def random_pairs(rng, count):
    pairs = []
    for _ in range(count):
        parent = random_policy(rng, rng.randint(1, 6))
        pairs.append({"child": child_of(rng, parent, 0.5), "parent": parent, "depth": 1})
    return pairs


def chain_pairs(rng, count, max_depth):
    pairs = []
    for _ in range(count):
        depth = rng.randint(1, max_depth)
        violation_depth = rng.randint(1, depth)
        current = random_policy(rng, rng.randint(2, 6))
        for hop in range(1, depth + 1):
            child = child_of(rng, current, 1.0 if hop == violation_depth else 0.0)
            pairs.append({"child": child, "parent": current, "depth": hop})
            current = child
    return pairs


def as_json_pair(pair):
    return {"child": [str(atom) for atom in pair["child"]], "parent": [str(atom) for atom in pair["parent"]]}


def go_decisions(pairs, mbla_binary):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as pairs_file:
        for pair in pairs:
            pairs_file.write(json.dumps(as_json_pair(pair)) + "\n")
    completed = subprocess.run([mbla_binary, "check", "-pairs", pairs_file.name], capture_output=True, text=True, check=True)
    Path(pairs_file.name).unlink()
    return [json.loads(line)["accepted"] for line in completed.stdout.splitlines()]


def summarize(pairs, decisions):
    expected = [reference.within(pair["child"], pair["parent"]) for pair in pairs]
    valid = sum(expected)
    invalid = len(expected) - valid
    false_accepts = sum(1 for want, got in zip(expected, decisions) if got and not want)
    false_rejects = sum(1 for want, got in zip(expected, decisions) if want and not got)
    return {
        "pairs": len(pairs),
        "valid": valid,
        "invalid": invalid,
        "false_accepts": false_accepts,
        "false_rejects": false_rejects,
        "false_accept_rate": false_accepts / invalid if invalid else 0.0,
        "false_reject_rate": false_rejects / valid if valid else 0.0,
        "max_depth": max(pair["depth"] for pair in pairs),
    }


def main():
    parser = argparse.ArgumentParser(description="E7: Go attenuation checker vs independent reference semantics")
    parser.add_argument("--mbla", default="../mbla/bin/mbla")
    parser.add_argument("--pairs", type=int, default=10000)
    parser.add_argument("--chains", type=int, default=1000)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="results/tables/conformance.json")
    arguments = parser.parse_args()
    rng = random.Random(arguments.seed)
    pairs = random_pairs(rng, arguments.pairs) + chain_pairs(rng, arguments.chains, arguments.max_depth)
    summary = summarize(pairs, go_decisions(pairs, arguments.mbla))
    Path(arguments.out).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if summary["false_accepts"] or summary["false_rejects"]:
        raise SystemExit("conformance failed")


if __name__ == "__main__":
    main()
