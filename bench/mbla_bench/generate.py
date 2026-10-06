import argparse
import json
import random
from pathlib import Path

import yaml

from mbla_bench import reference

BREADTHS = ["narrow", "medium", "broad"]
VARIANTS = ["benign", "injection"]


def load_templates(template_dir):
    delegations = yaml.safe_load((template_dir / "delegations.yaml").read_text())
    tasks = yaml.safe_load((template_dir / "tasks.yaml").read_text())
    return delegations, tasks


def distinct(rng, pool, count):
    return rng.sample(pool, count)


def sample_binding(rng, pools):
    owner = rng.choice(pools["owner"])
    artifact, artifact2 = distinct(rng, pools["artifact"], 2)
    doc, doc2, other_doc = distinct(rng, pools["doc"], 3)
    channel, channel2, other_channel = distinct(rng, pools["channel"], 3)
    issue_number, issue_number2, other_issue = distinct(rng, range(1, 1000), 3)
    return {
        "owner": owner,
        "repo": rng.choice(pools["repo"]),
        "private": rng.choice(pools["private"]),
        "label": rng.choice(pools["label"]),
        "prefix": rng.choice(pools["prefix"]),
        "artifact": artifact,
        "artifact2": artifact2,
        "doc": doc,
        "doc2": doc2,
        "other_doc": other_doc,
        "channel": channel,
        "channel2": channel2,
        "other_channel": other_channel,
        "issue_number": issue_number,
        "issue_number2": issue_number2,
        "other_issue": other_issue,
    }


def fill_all(texts, values):
    return unique([text.format(**values) for text in texts])


def unique(texts):
    return list(dict.fromkeys(texts))


def reaches(policy_texts, needs_texts):
    policy = reference.parse_all(policy_texts)
    return all(reference.covered(policy, reference.parse(need)) for need in needs_texts)


def build_attacks(delegation, values, parent):
    attacks = []
    for attack in delegation["attacks"]:
        needs = fill_all(attack["needs"], values)
        attacks.append(
            {
                "id": attack["id"],
                "needs": needs,
                "injection": attack["injection"].format(**values),
                "reachable": reaches(parent, needs),
            }
        )
    return attacks


def build_item(task, delegation, breadth, binding_index, binding, variant):
    values = dict(binding)
    arguments = {key: value.format(**values) for key, value in task["arguments"].items()}
    values.update(arguments)
    reference_policy = fill_all(task["reference"] + delegation["baseline"], values)
    parent = unique(reference_policy + fill_all(delegation["runtime"] + delegation["extras"][breadth], values))
    attacks = build_attacks(delegation, values, parent)
    text = task["texts"][binding_index % len(task["texts"])]
    injected = attacks[binding_index % len(attacks)] if variant == "injection" else None
    if injected:
        text = text + " " + injected["injection"]
    return {
        "id": f"{task['template']}-{breadth}-b{binding_index}-{variant}",
        "template": task["template"],
        "delegation": task["delegation"],
        "workflow": delegation["workflow"],
        "hop": delegation["hop"],
        "split": task["split"],
        "breadth": breadth,
        "variant": variant,
        "injected_attack": injected["id"] if injected else None,
        "request": {
            "protocol": delegation["protocol"],
            "operation": delegation["operation"],
            "arguments": arguments,
            "text": text.format(**values),
            "history": delegation["history"],
            "manifest": fill_all(delegation["manifest"], values),
        },
        "parent": parent,
        "ceiling": delegation["ceiling"],
        "reference": reference_policy,
        "alternates": [],
        "attacks": [attack for attack in attacks if attack["reachable"]],
        "provenance": {"author": "template", "audited_by": [], "execution_validated": False},
    }


def generate_items(delegations, tasks, bindings_per_template):
    items = []
    for task in tasks:
        delegation = delegations["delegations"][task["delegation"]]
        for binding_index in range(bindings_per_template):
            binding = sample_binding(random.Random(f"{task['template']}-{binding_index}"), delegations["pools"])
            for breadth in BREADTHS:
                for variant in VARIANTS:
                    items.append(build_item(task, delegation, breadth, binding_index, binding, variant))
    return items


def write_splits(items, task_dir):
    task_dir.mkdir(parents=True, exist_ok=True)
    for split in sorted({item["split"] for item in items}):
        lines = [json.dumps(item) for item in items if item["split"] == split]
        (task_dir / f"{split}.jsonl").write_text("\n".join(lines) + "\n")
        print(f"{split}: {len(lines)} items")


def main():
    parser = argparse.ArgumentParser(description="generate benchmark items from templates")
    parser.add_argument("--templates", default="data/templates")
    parser.add_argument("--out", default="data/tasks")
    parser.add_argument("--bindings", type=int, default=4)
    arguments = parser.parse_args()
    delegations, tasks = load_templates(Path(arguments.templates))
    write_splits(generate_items(delegations, tasks, arguments.bindings), Path(arguments.out))


if __name__ == "__main__":
    main()


def write_latency_subset(test_path="data/tasks/test.jsonl", out_path="data/latency/latency.jsonl", per_template=5):
    items = [json.loads(line) for line in Path(test_path).read_text().splitlines() if line]
    chosen = []
    for template in sorted({item["template"] for item in items}):
        chosen += sorted((item for item in items if item["template"] == template), key=lambda item: item["id"])[:per_template]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("".join(json.dumps(item) + "\n" for item in chosen))
    print(f"{out_path}: {len(chosen)} items")
