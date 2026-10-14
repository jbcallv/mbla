import csv
import json
import random
from collections import defaultdict

from scipy.stats import beta, binom

from mbla_bench import stats
from mbla_bench.synth import label

SAMPLE_SIZE = 93
ALLOWED_ERRORS = 1
ERROR_BOUND = 0.05
SEED = "D-21-audit"
COLUMNS = ["item", "workflow", "family", "task", "arguments", "permission", "meaning", "needed", "note"]


def allocation(items, total):
    by_family = defaultdict(list)
    for item in items:
        by_family[item["template"]].append(item)
    shares = {family: total * len(members) / len(items) for family, members in by_family.items()}
    counts = {family: int(share) for family, share in shares.items()}
    for family in sorted(shares, key=lambda family: shares[family] - counts[family], reverse=True)[: total - sum(counts.values())]:
        counts[family] += 1
    return by_family, counts


def sample(items):
    by_family, counts = allocation(items, SAMPLE_SIZE)
    rng = random.Random(SEED)
    return [item for family in sorted(counts) for item in rng.sample(sorted(by_family[family], key=lambda entry: entry["id"]), counts[family])]


def meaning(permission, glossary):
    service, operation, _ = permission.split(":", 2)
    return glossary.get(f"{service}:{operation}", "")


def sheet_rows(item, glossary):
    pool = label.candidates(item["parent"], item["request"]["arguments"])
    return [
        {
            "item": item["id"],
            "workflow": item["workflow"],
            "family": item["template"],
            "task": item["request"]["text"],
            "arguments": json.dumps(item["request"]["arguments"]),
            "permission": permission,
            "meaning": meaning(permission, glossary),
            "needed": "",
            "note": "",
        }
        for permission in pool
    ]


def write_sheet(path, chosen, glossary):
    with open(path, "w", newline="") as sheet:
        writer = csv.DictWriter(sheet, COLUMNS)
        writer.writeheader()
        for item in chosen:
            writer.writerows(sheet_rows(item, glossary))


def read_needed(path):
    with open(path, newline="", encoding="utf-8-sig") as sheet:
        return {(row["item"], row["permission"]): row["needed"].strip() in ("1", "yes", "y", "true") for row in csv.DictReader(sheet)}


def human_sets(decisions):
    sets = defaultdict(set)
    for (item, permission), needed in decisions.items():
        sets[item]
        if needed:
            sets[item].add(permission)
    return sets


def acceptance(errors, size=SAMPLE_SIZE):
    return {
        "sample": size,
        "errors": errors,
        "passes": errors <= ALLOWED_ERRORS,
        "error_rate_upper_95": float(beta.ppf(0.95, errors + 1, size - errors)) if errors < size else 1.0,
        "chance_of_passing_if_true_rate_is_bound": float(binom.cdf(ALLOWED_ERRORS, size, ERROR_BOUND)),
    }


def score(first_path, second_path, adjudicated_path, items_by_id):
    first, second, settled = read_needed(first_path), read_needed(second_path), read_needed(adjudicated_path)
    shared = sorted(set(first) & set(second))
    generated = {item: set(items_by_id[item]["reference"]) for item in human_sets(settled)}
    wrong = sorted(item for item, needed in human_sets(settled).items() if needed != generated[item])
    return {
        "decisions": len(shared),
        "kappa_reviewers": stats.cohen_kappa([first[key] for key in shared], [second[key] for key in shared]),
        "kappa_settled_vs_generated": stats.cohen_kappa(
            [settled[key] for key in sorted(settled)], [key[1] in generated[key[0]] for key in sorted(settled)]
        ),
        "wrong_items": wrong,
        **acceptance(len(wrong)),
    }
