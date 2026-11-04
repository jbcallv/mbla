"""plans broken on purpose: how often a judge still accepts them shows whether its filter has teeth."""
import json
import random
from pathlib import Path

from mbla_bench import data
from mbla_bench.synth.run import WORK

SIZE = 200
SEED = "judge-check"


def dropped(task, rng):
    plan = list(task["plan"])
    plan.pop(rng.randrange(len(plan)))
    return {**task, "plan": plan, "corruption": "dropped"}


def extra(task, others, rng):
    call = rng.choice(rng.choice(others)["plan"])
    plan = list(task["plan"])
    plan.insert(rng.randrange(len(plan) + 1), call)
    return {**task, "plan": plan, "corruption": "extra"}


def main():
    rng = random.Random(SEED)
    tasks = sorted(data.read_jsonl(WORK / "filtered.jsonl"), key=lambda task: task["id"])
    longer = [task for task in tasks if len(task["plan"]) > 1]
    broken = [dropped(task, rng) for task in rng.sample(longer, SIZE)]
    for task in rng.sample(tasks, SIZE):
        others = [other for other in tasks if other["family"] != task["family"]]
        broken.append(extra(task, others, rng))
    (WORK / "corrupted.jsonl").write_text("".join(json.dumps(task) + "\n" for task in broken))
    print(len(broken), "broken plans")


if __name__ == "__main__":
    main()
