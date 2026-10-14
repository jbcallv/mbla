import argparse
import json
import re

from mbla_bench import data, reference
from mbla_bench.synth import vocabulary

TEMPLATE_PLANS = "data/synth/template_plans.yaml"
CHECK_BINDING = {
    "owner": "acme",
    "repo": "web",
    "issue_number": 42,
    "issue_number2": 57,
    "label": "bug",
    "prefix": "releases",
    "artifact": "site.zip",
    "artifact2": "app.tar.gz",
    "doc": "roadmap-2026",
    "doc2": "q3-planning",
    "channel": "eng-updates",
    "channel2": "release-notes",
    "region": "us-east-1",
}


def minimal(permissions):
    unique = list(dict.fromkeys(permissions))
    atoms = reference.parse_all(unique)
    kept = []
    for index, atom in enumerate(atoms):
        broader = [other for other_index, other in enumerate(atoms) if other_index != index and other != atom and reference.within([atom], [other])]
        if not broader:
            kept.append(unique[index])
    return sorted(kept)


def label(plan, vocab, values):
    needed = []
    for call in plan:
        arguments = {**values, **{key: vocabulary.fill(str(value), values) for key, value in call.get("with", {}).items()}}
        needed += vocabulary.call_permissions(vocab, call, arguments)
    return minimal(needed)


def human_key(task, delegation, values):
    return sorted(vocabulary.fill(permission, values) for permission in task["reference"] + delegation["baseline"])


def check_templates():
    vocab = vocabulary.load()
    plans = data.load_yaml(TEMPLATE_PLANS)
    delegations = data.load_yaml("data/templates/delegations.yaml")["delegations"]
    results = []
    for task in data.load_yaml("data/templates/tasks.yaml"):
        values = {**CHECK_BINDING, **{key: vocabulary.fill(value, CHECK_BINDING) for key, value in task["arguments"].items()}}
        generated = label(plans[task["template"]], vocab, values)
        human = human_key(task, delegations[task["delegation"]], values)
        results.append({"template": task["template"], "agrees": generated == human, "generated": generated, "human": human})
    return results


def main():
    argparse.ArgumentParser(description="label the benchmark templates from call plans and compare with the human-reviewed keys").parse_args()
    results = check_templates()
    for result in results:
        if not result["agrees"]:
            print(json.dumps(result))
    print(f"{sum(result['agrees'] for result in results)}/{len(results)} templates: generated key equals the human-reviewed key")
    items = check_items(["data/tasks/dev.jsonl", "data/tasks/test.jsonl"])
    for result in items:
        if not result["agrees"]:
            print(json.dumps(result))
    print(f"{sum(result['agrees'] for result in items)}/{len(items)} items: training labels over the candidate pool equal the human-reviewed reference")



def candidates(holdings, arguments):
    pool = list(holdings)
    for holding in reference.parse_all(holdings):
        if holding.kind != "C":
            continue
        for value in [arguments[key] for key in sorted(arguments)]:
            concrete = reference.Atom(holding.service, holding.operation, value, holding.qualifier)
            if reference.grants(holding, concrete) and str(concrete) not in pool:
                pool.append(str(concrete))
    return pool


def narrowest_cover(atom, pool):
    covering = [candidate for candidate in pool if reference.grants(reference.parse(candidate), atom)]
    narrowest = [candidate for candidate in covering if all(reference.within([reference.parse(candidate)], [reference.parse(other)]) for other in covering)]
    return narrowest[0] if narrowest else None


def candidate_labels(key, pool):
    chosen = [narrowest_cover(atom, pool) for atom in reference.parse_all(key)]
    if None in chosen:
        return None
    return sorted(set(chosen))


def item_values(item, tasks, pools):
    from mbla_bench import generate

    task = tasks[item["template"]]
    binding_index = int(re.search(r"-b(\d+)-", item["id"]).group(1))
    values = generate.sample_binding(generate.random.Random(f"{item['template']}-{binding_index}"), pools)
    values["region"] = CHECK_BINDING["region"]
    values.update({key: vocabulary.fill(value, values) for key, value in task["arguments"].items()})
    return values


def check_items(item_paths):
    vocab = vocabulary.load()
    plans = data.load_yaml(TEMPLATE_PLANS)
    pools = data.load_yaml("data/templates/delegations.yaml")["pools"]
    tasks = {task["template"]: task for task in data.load_yaml("data/templates/tasks.yaml")}
    results = []
    for path in item_paths:
        for item in data.items_by_id(path).values():
            values = item_values(item, tasks, pools)
            key = label(plans[item["template"]], vocab, values)
            chosen = candidate_labels(key, candidates(item["parent"], item["request"]["arguments"]))
            results.append({"item": item["id"], "agrees": chosen == sorted(item["reference"]), "generated": chosen, "human": sorted(item["reference"])})
    return results


if __name__ == "__main__":
    main()
