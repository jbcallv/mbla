import argparse
import json
import re

from mbla_bench import answer, data, generate, reference
from mbla_bench.synth import vocabulary

TEMPLATE_PLANS = "data/synth/template_plans.yaml"


def minimal(permissions):
    """the log, with every permission covered by a stronger one in the log removed."""
    unique = list(dict.fromkeys(permissions))
    atoms = reference.parse_all(unique)
    return sorted(text for index, text in enumerate(unique) if not any(other != atoms[index] and reference.within([atoms[index]], [other]) for other in atoms))


def label(plan, vocab, values):
    needed = []
    for call in plan:
        arguments = {**values, **{key: vocabulary.fill(str(value), values) for key, value in call.get("with", {}).items()}}
        needed += vocabulary.call_permissions(vocab, call, arguments)
    return minimal(needed)


def template_values(values):
    return {**values, "workspace": values["workspace_id"], "channel_id": values["channel_id"], "channel2_id": values["channel2_id"]}


def check_templates():
    """the labeler reproduces the development answer keys from call plans, on all 408 tasks (checks the labeler's code only)."""
    vocab = vocabulary.load()
    plans = data.load_yaml(TEMPLATE_PLANS)
    pools = data.load_yaml("data/templates/delegations.yaml")["pools"]
    results = []
    for item in data.read_jsonl("data/tasks/dev.jsonl"):
        index = int(re.search(r"-b(\d+)-", item["id"]).group(1))
        values = template_values(generate.sample_binding(generate.random.Random(f"{item['template']}-{index}"), pools))
        generated = label(plans[item["template"]], vocab, values)
        results.append({"item": item["id"], "agrees": generated == minimal(item["plans"][0]), "generated": generated, "key": sorted(item["plans"][0])})
    return results


def main():
    argparse.ArgumentParser(description="label the development templates from call plans and compare with their keys").parse_args()
    results = check_templates()
    wrong = [result for result in results if not result["agrees"]]
    for result in {result["item"].split("-narrow")[0].split("-medium")[0].split("-broad")[0]: result for result in wrong}.values():
        print(json.dumps(result))
    print(f"{len(results) - len(wrong)}/{len(results)} tasks: generated key equals the development key")


if __name__ == "__main__":
    main()
