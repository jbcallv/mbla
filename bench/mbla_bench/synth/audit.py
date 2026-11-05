"""the 93-task human check of the synthetic keys: two people label blind, settle differences, at most one task may be wrong."""
import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

from scipy.stats import beta, binom

from mbla_bench import answer, data, stats
from mbla_bench.review_sample import meanings
from mbla_bench.synth.run import SIZES

SAMPLE_SIZE = 93
ALLOWED_ERRORS = 1
ERROR_BOUND = 0.05
SEED = "D-21-audit"
SHEET = "../share/synth_check_sheet.csv"
KEY = "data/review/synth/key.csv"
SEEN = "data/review/synth_seen.txt"
SHEET_COLUMNS = ["row", "item", "task", "receiver", "permission", "meaning", "answer", "note"]
KEY_COLUMNS = ["row", "item", "family", "split", "permission", "generated"]


def items():
    return [item for split in SIZES for item in data.read_jsonl(f"data/tasks/synth_{split}.jsonl")]


def allocation(tasks, total):
    by_family = defaultdict(list)
    for task in tasks:
        by_family[task["template"]].append(task)
    shares = {family: total * len(members) / len(tasks) for family, members in by_family.items()}
    counts = {family: int(share) for family, share in shares.items()}
    for family in sorted(shares, key=lambda family: shares[family] - counts[family], reverse=True)[: total - sum(counts.values())]:
        counts[family] += 1
    return by_family, counts


def unseen(tasks):
    """tasks shown with their answers in the preview would not be blind, so they cannot enter the sample."""
    seen = tuple(f"{line.strip()}-" for line in Path(SEEN).read_text().splitlines())
    return [task for task in tasks if not task["id"].startswith(seen)]


def sample(tasks):
    by_family, counts = allocation(unseen(tasks), SAMPLE_SIZE)
    rng = random.Random(SEED)
    return [task for family in sorted(counts) for task in rng.sample(sorted(by_family[family], key=lambda entry: entry["id"]), counts[family])]


def meaning_of(permission, glossary):
    service, operation = permission.split(":")[:2]
    return glossary.get(f"{service}:{operation}", "")


def rows_of(task, glossary):
    required, plausible = answer.tiers(task)
    tier = {**{str(atom): "plausible" for atom in plausible}, **{str(atom): "required" for atom in required}}
    return [
        {
            "item": task["id"],
            "family": task["template"],
            "split": task["split"],
            "task": task["request"]["text"],
            "receiver": task["request"]["receiver"]["name"],
            "permission": str(atom),
            "meaning": meaning_of(str(atom), glossary),
            "generated": tier.get(str(atom), "unneeded"),
        }
        for atom in answer.candidates(task)
    ]


def write(path, columns, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as sheet:
        writer = csv.DictWriter(sheet, columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def make_sheet():
    glossary = meanings()
    chosen = sample(items())
    rng = random.Random(SEED)
    rng.shuffle(chosen)
    rows = [row for task in chosen for row in rows_of(task, glossary)]
    for number, row in enumerate(rows, 1):
        row["row"] = number
    write(SHEET, SHEET_COLUMNS, rows)
    write(KEY, KEY_COLUMNS, rows)
    print(len(chosen), "tasks,", len(rows), "rows")


def read_answers(path):
    with open(path, newline="", encoding="utf-8-sig") as sheet:
        return {row["row"]: row["answer"].strip().lower() for row in csv.DictReader(sheet)}


def wrong_tasks(settled, key):
    return sorted({entry["item"] for entry in key if settled[entry["row"]] != entry["generated"]})


def acceptance(errors, size=SAMPLE_SIZE):
    return {
        "sample": size,
        "errors": errors,
        "passes": errors <= ALLOWED_ERRORS,
        "error_rate_upper_95": float(beta.ppf(0.95, errors + 1, size - errors)) if errors < size else 1.0,
        "chance_of_passing_if_true_rate_is_bound": float(binom.cdf(ALLOWED_ERRORS, size, ERROR_BOUND)),
    }


def score(first_path, second_path, settled_path):
    first, second, settled = read_answers(first_path), read_answers(second_path), read_answers(settled_path)
    with open(KEY, newline="") as sheet:
        key = list(csv.DictReader(sheet))
    rows = [entry["row"] for entry in key]
    wrong = wrong_tasks(settled, key)
    return {
        "decisions": len(rows),
        "kappa_reviewers": stats.cohen_kappa([first[row] for row in rows], [second[row] for row in rows]),
        "kappa_settled_vs_generated": stats.cohen_kappa([settled[entry["row"]] for entry in key], [entry["generated"] for entry in key]),
        "wrong_items": wrong,
        **acceptance(len(wrong)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["sheet", "score"])
    parser.add_argument("--first")
    parser.add_argument("--second")
    parser.add_argument("--settled")
    arguments = parser.parse_args()
    if arguments.stage == "sheet":
        make_sheet()
    else:
        print(score(arguments.first, arguments.second, arguments.settled))


if __name__ == "__main__":
    main()
