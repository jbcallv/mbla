"""model choice for the synthetic set: judges scored on known-good and broken plans, the rule fixed before any candidate ran (D-40)."""
import json
import re
import sys

from mbla_bench import data, generate
from mbla_bench.synth import label
from mbla_bench.synth.run import WORK

KNOWN_GOOD = WORK / "known_good.jsonl"
BROKEN = WORK / "corrupted.jsonl"


def filled(call, values):
    return {"name": call["name"], "with": {name: str(value).format_map(values) for name, value in call.get("with", {}).items()}}


def known_good():
    plans = data.load_yaml(label.TEMPLATE_PLANS)
    pools = data.load_yaml("data/templates/delegations.yaml")["pools"]
    found = {}
    for item in data.read_jsonl("data/tasks/dev.jsonl"):
        if item["variant"] == "benign":
            index = int(re.search(r"-b(\d+)-", item["id"]).group(1))
            values = label.template_values(generate.sample_binding(generate.random.Random(f"{item['template']}-{index}"), pools))
            plan = [filled(call, values) for call in plans[item["template"]]]
            found.setdefault(item["request"]["text"], {"id": item["id"], "family": item["template"], "text": item["request"]["text"], "plan": plan})
    return list(found.values())


def accepted(path):
    return {json.loads(line)["id"] for line in open(path)}


def broken_kept(path):
    return {(task["id"], task["corruption"]) for task in data.read_jsonl(path)}


def score(names):
    """a verdict set per judge name: <name>_good.jsonl and <name>_broken.jsonl in bakeoff/."""
    good = [task["id"] for task in data.read_jsonl(KNOWN_GOOD)]
    kept = {name: (accepted(WORK / f"bakeoff/{name}_good.jsonl"), broken_kept(WORK / f"bakeoff/{name}_broken.jsonl")) for name in names}
    print("judge(s)                     good kept   dropped kept   extra kept")
    rows = [(name,) for name in names] + [(first, second) for index, first in enumerate(names) for second in names[index + 1 :]]
    for pair in rows:
        passed = set.intersection(*[kept[name][0] for name in pair])
        leaked = set.intersection(*[kept[name][1] for name in pair])
        print(f"{'+'.join(pair):28} {len(passed):3}/{len(good)}  {sum(kind == 'dropped' for _, kind in leaked):3}/200  {sum(kind == 'extra' for _, kind in leaked):3}/200")


if __name__ == "__main__":
    if sys.argv[1] == "known-good":
        tasks = known_good()
        KNOWN_GOOD.write_text("".join(json.dumps(task) + "\n" for task in tasks))
        print(len(tasks), "known-good tasks", len({task["family"] for task in tasks}), "templates")
    else:
        score(sys.argv[2:])
