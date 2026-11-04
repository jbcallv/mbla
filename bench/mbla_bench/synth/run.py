"""builds the synthetic set: a local model writes tasks and call plans, a mock service labels them, two judges filter them."""
import argparse
import json
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from pathlib import Path

import requests

from mbla_bench import data
from mbla_bench.synth import assemble, decontaminate, execute, holdings, holdout, judge, vocabulary, write

FAMILIES = "data/synth/families.yaml"
WORK = Path("data/synth/work")
RAW = WORK / "raw.jsonl"
RAW_TOPUP = WORK / "raw_topup.jsonl"
JUDGED = WORK / "judged.jsonl"
FIRST_TOPUP_SEED = 2000
TOPUP_MARGIN = 1.1
MAX_TOPUP_REQUESTS = 45
SIZES = {"train": 1500, "validation": 300, "heldout": 200}
OVERSAMPLE = 2.6
CONCURRENCY = 8


def chat(endpoint, model, system, user, schema, max_tokens, temperature=0.7):
    body = {"model": model, "temperature": temperature, "seed": 0, "max_tokens": max_tokens, "response_format": schema, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    response = requests.post(f"{endpoint}/chat/completions", json=body, timeout=900)
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def write_request(arguments, families, family, names, vocab, seed):
    rng = random.Random(f"{family['id']}-{seed}")
    chosen = write.sample_names(rng, names)
    prompt = write.writer_prompt(family, write.handoff_of(family, families)[1], chosen, vocab)
    try:
        response = chat(arguments.endpoint, arguments.model, write.WRITER_INSTRUCTIONS, prompt, write.writer_schema(family, vocab), 4096)
    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
        print(family["id"], seed, "failed:", error, flush=True)
        return []
    return [{**task, "writer": arguments.model} for task in write.tasks_from(response, family, names, chosen, seed)]


def write_all(arguments):
    families = data.load_yaml(FAMILIES)
    names, vocab = data.load_yaml(write.NAMES), vocabulary.load()
    outside = set(holdout.held_out(families["families"]))
    train_families = len(families["families"]) - len(outside)
    wanted = {True: SIZES["heldout"] / len(outside), False: (SIZES["train"] + SIZES["validation"]) / train_families}
    jobs = []
    for family in families["families"]:
        requests_needed = round(wanted[family["id"] in outside] * OVERSAMPLE * arguments.scale / write.TASKS_PER_REQUEST + 0.5)
        jobs += [(family, seed) for seed in range(requests_needed)]
    WORK.mkdir(parents=True, exist_ok=True)
    raw = Path(arguments.raw)
    with ThreadPoolExecutor(CONCURRENCY) as pool, raw.open("a") as out:
        for batch in pool.map(lambda job: write_request(arguments, families, job[0], names, vocab, job[1]), jobs):
            out.writelines(json.dumps(task) + "\n" for task in batch)
            out.flush()
    print(f"{len(jobs)} requests; {sum(1 for _ in raw.open())} tasks", flush=True)


def topup_jobs(families, kept):
    """more requests only where the first pass fell short, sized by each family's observed yield."""
    raw, have = Counter(task["family"] for task in data.read_jsonl(RAW)), Counter(task["family"] for task in kept)
    outside = set(holdout.held_out(families))
    target = {True: SIZES["heldout"] / len(outside), False: (SIZES["train"] + SIZES["validation"]) / (len(families) - len(outside))}
    jobs = []
    for family in families:
        gap = target[family["id"] in outside] * TOPUP_MARGIN - have[family["id"]]
        rate = max(have[family["id"]] / max(raw[family["id"]], 1), 0.1)
        count = min(ceil(gap / (write.TASKS_PER_REQUEST * rate)), MAX_TOPUP_REQUESTS) if gap > 0 else 0
        jobs += [(family, FIRST_TOPUP_SEED + seed) for seed in range(count)]
    return jobs


def topup_all(arguments):
    families = data.load_yaml(FAMILIES)
    names, vocab = data.load_yaml(write.NAMES), vocabulary.load()
    kept = data.read_jsonl(JUDGED)
    jobs = topup_jobs(families["families"], kept)
    print(len(kept), "kept;", len(jobs), "requests", flush=True)
    with ThreadPoolExecutor(CONCURRENCY) as pool, RAW_TOPUP.open("a") as out:
        for batch in pool.map(lambda job: write_request(arguments, families, job[0], names, vocab, job[1]), jobs):
            out.writelines(json.dumps(task) + "\n" for task in batch)
            out.flush()
    print(sum(1 for _ in RAW_TOPUP.open()), "tasks", flush=True)


def filter_topup(arguments):
    kept = data.read_jsonl(JUDGED)
    earlier = {task["id"] for task in kept}
    raw = data.read_jsonl(RAW_TOPUP)
    ran = executed(raw, vocabulary.load())
    fresh = [task for task in clean(kept + ran) if task["id"] not in earlier]
    print(f"topup raw {len(raw)}, executed {len(ran)}, after leak and duplicate filters {len(fresh)}", flush=True)
    (WORK / "filtered_topup.jsonl").write_text("".join(json.dumps(task) + "\n" for task in fresh))


def executed(tasks, vocab):
    kept = []
    for task in tasks:
        problems, _ = execute.run(vocab, task)
        if not problems:
            kept.append(task)
    return kept


def clean(tasks):
    forbidden = decontaminate.benchmark_ngrams(["data/tasks/dev.jsonl", "data/tasks/test.jsonl"])
    by_family = {}
    for task in tasks:
        if not decontaminate.leaks(task, forbidden):
            by_family.setdefault(task["family"], []).append(task)
    return [task for family in by_family.values() for task in decontaminate.without_near_duplicates(family)]


def judge_all(arguments, tasks, vocab, out):
    tasks = tasks[: arguments.limit]

    def verdict(task):
        try:
            return (chat(arguments.endpoint, arguments.model, judge.JUDGE_INSTRUCTIONS, judge.judge_prompt(task, vocab), judge.judge_schema(len(task["plan"])), 512, 0))
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            print(task["id"], "judge failed:", error, flush=True)
            return None

    with ThreadPoolExecutor(CONCURRENCY) as pool:
        verdicts = list(pool.map(verdict, tasks))
    kept = [{**task, "judges": task.get("judges", []) + [arguments.model]} for task, found in zip(tasks, verdicts) if found and judge.accepted(found)]
    Path(out).write_text("".join(json.dumps(task) + "\n" for task in kept))
    Path(f"{out}.verdicts").write_text("".join(json.dumps({"id": task["id"], "verdict": found}) + "\n" for task, found in zip(tasks, verdicts)))
    print(f"judge {arguments.model}: {len(kept)} of {len(tasks)} accepted, {verdicts.count(None)} failed requests", flush=True)


def filter_tasks(arguments):
    vocab = vocabulary.load()
    raw = data.read_jsonl(RAW)
    ran = executed(raw, vocab)
    kept = clean(ran)
    print(f"raw {len(raw)}, executed {len(ran)}, after leak and duplicate filters {len(kept)}", flush=True)
    (WORK / "filtered.jsonl").write_text("".join(json.dumps(task) + "\n" for task in kept))


def split_of(family, tasks, outside, rng):
    tasks = sorted(tasks, key=lambda task: task["id"])
    rng.shuffle(tasks)
    if family in outside:
        return [(task, "heldout") for task in tasks]
    cut = len(tasks) * SIZES["train"] // (SIZES["train"] + SIZES["validation"])
    return [(task, "train") for task in tasks[:cut]] + [(task, "validation") for task in tasks[cut:]]


def capped(tasks, size):
    """at most size tasks, cutting the largest families first."""
    by_family = {}
    for task in tasks:
        by_family.setdefault(task[0]["family"], []).append(task)
    cap = max(len(members) for members in by_family.values())
    while sum(min(len(members), cap) for members in by_family.values()) > size:
        cap -= 1
    return [task for members in by_family.values() for task in members[:cap]]


def assemble_all(arguments):
    families = data.load_yaml(FAMILIES)
    specs = {family["id"]: family for family in families["families"]}
    vocab, by_service, meaning = vocabulary.load(), holdings.operations(), assemble.descriptions()
    outside = set(holdout.held_out(families["families"]))
    by_family = {}
    for task in data.read_jsonl(arguments.input):
        by_family.setdefault(task["family"], []).append(task)
    rng = random.Random("D-36-synth")
    outputs = {split: [] for split in SIZES}
    placed = [pair for family, tasks in sorted(by_family.items()) for pair in split_of(family, tasks, outside, rng)]
    kept = [pair for split in SIZES for pair in capped([pair for pair in placed if pair[1] == split], SIZES[split])]
    for family in sorted(by_family):
        handoff, spec = write.handoff_of(specs[family], families)
        for task, split in [pair for pair in kept if pair[0]["family"] == family]:
            outputs[split].append(assemble.build_item(task, specs[family], handoff, spec, rng.choice(holdings.BREADTHS), rng.choice(["benign", "injection"]), split, vocab, by_service, meaning))
    for split, items in outputs.items():
        Path(f"data/tasks/synth_{split}.jsonl").write_text("".join(json.dumps(item) + "\n" for item in items))
        print(split, len(items), "of", SIZES[split], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["write", "topup", "filter", "filter-topup", "judge", "assemble"])
    parser.add_argument("--endpoint")
    parser.add_argument("--model")
    parser.add_argument("--input", default=str(WORK / "filtered.jsonl"))
    parser.add_argument("--out", default=str(WORK / "judged.jsonl"))
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--raw", default=str(RAW))
    arguments = parser.parse_args()
    if arguments.stage == "write":
        write_all(arguments)
    elif arguments.stage == "topup":
        topup_all(arguments)
    elif arguments.stage == "filter":
        filter_tasks(arguments)
    elif arguments.stage == "filter-topup":
        filter_topup(arguments)
    elif arguments.stage == "judge":
        judge_all(arguments, data.read_jsonl(arguments.input), vocabulary.load(), arguments.out)
    else:
        assemble_all(arguments)


if __name__ == "__main__":
    main()
