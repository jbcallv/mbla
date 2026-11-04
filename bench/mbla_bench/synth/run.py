"""builds the synthetic set: a local model writes tasks and call plans, a mock service labels them, two judges filter them."""
import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from mbla_bench import data
from mbla_bench.synth import assemble, decontaminate, execute, holdings, holdout, judge, vocabulary, write

FAMILIES = "data/synth/families.yaml"
WORK = Path("data/synth/work")
RAW = WORK / "raw.jsonl"
SIZES = {"train": 1500, "validation": 300, "heldout": 200}
OVERSAMPLE = 1.6
CONCURRENCY = 8


def chat(endpoint, model, system, user, schema, max_tokens):
    body = {"model": model, "temperature": 0.7, "max_tokens": max_tokens, "response_format": schema, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    response = requests.post(f"{endpoint}/chat/completions", json=body, timeout=900)
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def write_request(arguments, families, family, names, vocab, seed):
    rng = random.Random(f"{family['id']}-{seed}")
    chosen = write.sample_names(rng, names)
    prompt = write.writer_prompt(family, write.handoff_of(family, families)[1], chosen, vocab)
    try:
        response = chat(arguments.endpoint, arguments.model, write.WRITER_INSTRUCTIONS, prompt, write.writer_schema(family), 4096)
    except (requests.RequestException, json.JSONDecodeError, KeyError) as error:
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
    with ThreadPoolExecutor(CONCURRENCY) as pool, RAW.open("a") as out:
        for batch in pool.map(lambda job: write_request(arguments, families, job[0], names, vocab, job[1]), jobs):
            out.writelines(json.dumps(task) + "\n" for task in batch)
            out.flush()
    print(f"{len(jobs)} requests; {sum(1 for _ in RAW.open())} tasks", flush=True)


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
    def verdict(task):
        try:
            return judge.accepted(chat(arguments.endpoint, arguments.model, judge.JUDGE_INSTRUCTIONS, judge.judge_prompt(task, vocab), judge.judge_schema(len(task["plan"])), 512))
        except (requests.RequestException, json.JSONDecodeError, KeyError):
            return False

    with ThreadPoolExecutor(CONCURRENCY) as pool:
        verdicts = list(pool.map(verdict, tasks))
    kept = [{**task, "judges": task.get("judges", []) + [arguments.model]} for task, accepted in zip(tasks, verdicts) if accepted]
    Path(out).write_text("".join(json.dumps(task) + "\n" for task in kept))
    print(f"judge {arguments.model}: {len(kept)} of {len(tasks)} accepted", flush=True)


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
    for family, tasks in sorted(by_family.items()):
        handoff, spec = write.handoff_of(specs[family], families)
        for task, split in split_of(family, tasks, outside, rng):
            outputs[split].append(assemble.build_item(task, specs[family], handoff, spec, rng.choice(holdings.BREADTHS), rng.choice(["benign", "injection"]), split, vocab, by_service, meaning))
    for split, items in outputs.items():
        Path(f"data/tasks/synth_{split}.jsonl").write_text("".join(json.dumps(item) + "\n" for item in items))
        print(split, len(items), "of", SIZES[split], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["write", "filter", "judge", "assemble"])
    parser.add_argument("--endpoint")
    parser.add_argument("--model")
    parser.add_argument("--input", default=str(WORK / "filtered.jsonl"))
    parser.add_argument("--out", default=str(WORK / "judged.jsonl"))
    parser.add_argument("--scale", type=float, default=1.0)
    arguments = parser.parse_args()
    if arguments.stage == "write":
        write_all(arguments)
    elif arguments.stage == "filter":
        filter_tasks(arguments)
    elif arguments.stage == "judge":
        judge_all(arguments, data.read_jsonl(arguments.input), vocabulary.load(), arguments.out)
    else:
        assemble_all(arguments)


if __name__ == "__main__":
    main()
