import argparse
import hashlib
import json
import random
from pathlib import Path

import yaml

from mbla_bench import reference

BREADTHS = ["narrow", "medium", "broad"]
VARIANTS = ["benign", "injection"]


def load_templates(template_dir, split):
    delegations = yaml.safe_load((template_dir / "delegations.yaml").read_text())
    tasks = yaml.safe_load((template_dir / f"{split}.yaml").read_text())
    return delegations, tasks


def slack_id(prefix, name):
    return prefix + hashlib.sha256(name.encode()).hexdigest()[:8].upper()


def sample_binding(rng, pools):
    """same draws, in the same order, as the pilot, so each task keeps its pilot names."""
    owner = rng.choice(pools["owner"])
    artifact, artifact2 = rng.sample(pools["artifact"], 2)
    doc, doc2, other_doc = rng.sample(pools["doc"], 3)
    channel, channel2, other_channel = rng.sample(pools["channel"], 3)
    issue_number, issue_number2, other_issue = rng.sample(range(1, 1000), 3)
    binding = {
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
    binding["workspace_id"] = slack_id("T", owner)
    for key in ("channel", "channel2", "other_channel"):
        binding[f"{key}_id"] = slack_id("C", owner + "/" + binding[key])
    return binding


def unique(texts):
    return list(dict.fromkeys(texts))


def fill_all(texts, values, delegations, workflow):
    filled = []
    for text in texts:
        if text == "{decoys}":
            filled += delegations["decoys"]
        elif text == "{volumes}":
            filled += [f"fs:rw:{volume}" for volume in delegations["volumes"][workflow]]
        else:
            filled.append(text.format(**values))
    return unique(filled)


def strongest_mounts(texts):
    """a delegator holds each volume once; a read-write mount replaces the same volume read-only."""
    writable = {text.split(":", 2)[2] for text in texts if text.startswith("fs:rw:")}
    return [text for text in texts if not (text.startswith("fs:ro:") and text.split(":", 2)[2] in writable)]


def reaches(parent, needs):
    policy = reference.parse_all(parent)
    return all(reference.covered(policy, reference.parse(need)) for need in needs)


def named_resources(texts):
    atoms = [reference.parse(text) for text in texts]
    return [f"{atom.service}:{atom.resource.removesuffix('*')}" for atom in atoms if atom.kind == "C"]


def build_attacks(delegation, values):
    return [
        {"id": attack["id"], "needs": [need.format(**values) for need in attack["needs"]], "injection": attack["injection"].format(**values)}
        for attack in delegation["attacks"]
        if "dropped" not in attack
    ]


def build_item(task, delegations, breadth, binding_index, values, variant, split):
    delegation = delegations["delegations"][task["delegation"]]
    workflow, remote = delegation["workflow"], delegation["receiver"]["remote"]
    plans = [fill_all(plan, values, delegations, workflow) for plan in task["plans"]]
    held = [need for plan in plans for need in plan] + delegation["runtime"] + delegation["extras"][breadth]
    parent = strongest_mounts(fill_all(held, values, delegations, workflow))
    attacks = build_attacks(delegation, values)
    injected = attacks[binding_index % len(attacks)] if variant == "injection" else None
    text = task["texts"][binding_index % len(task["texts"])].format(**values)
    named = [need for plan in plans for need in plan] + (injected["needs"] if injected else [])
    return {
        "id": f"{task['template']}-{breadth}-b{binding_index}-{variant}",
        "template": task["template"],
        "handoff": task["delegation"],
        "workflow": workflow,
        "hop": delegation["hop"],
        "split": split,
        "breadth": breadth,
        "variant": variant,
        "injected_attack": injected["id"] if injected else None,
        "request": {
            "protocol": delegation["protocol"],
            "operation": delegation["operation"],
            "receiver": delegation["receiver"],
            "text": text + (" " + injected["injection"] if injected else ""),
            "history": delegation["history"],
            "manifest": fill_all(delegation["manifest"], values, delegations, workflow),
            "named": unique(named_resources(named)),
        },
        "parent": parent,
        "ceiling": [] if remote else [text for text in parent if text.split(":", 1)[0] in ("net", "fs")],
        "plans": plans,
        "attacks": [attack for attack in attacks if reaches(parent, attack["needs"])],
        "provenance": {"author": "template", "converted_from": "pilot" if split == "dev" else None, "reviewed_by": []},
    }


def generate_items(delegations, tasks, bindings_per_template, split):
    items = []
    for task in tasks:
        for binding_index in range(bindings_per_template):
            values = sample_binding(random.Random(f"{task['template']}-{binding_index}"), delegations["pools"])
            for breadth in BREADTHS:
                for variant in VARIANTS:
                    items.append(build_item(task, delegations, breadth, binding_index, values, variant, split))
    return items


def main():
    parser = argparse.ArgumentParser(description="generate benchmark tasks from templates")
    parser.add_argument("--templates", default="data/templates")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--out", default="data/tasks")
    parser.add_argument("--bindings", type=int, default=4)
    arguments = parser.parse_args()
    delegations, tasks = load_templates(Path(arguments.templates), arguments.split)
    items = generate_items(delegations, tasks, arguments.bindings, arguments.split)
    out = Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{arguments.split}.jsonl").write_text("".join(json.dumps(item) + "\n" for item in items))
    print(f"{arguments.split}: {len(items)} tasks")


if __name__ == "__main__":
    main()
