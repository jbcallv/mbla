"""labeling sheets and agreement for the answer keys (final methodology §5, labeling; research/labeling_guide.md)."""

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from mbla_bench import answer, conversion, data, generate, reference, stats

TIERS = {"r": "required", "required": "required", "p": "plausible", "plausible": "plausible", "u": "unneeded", "unneeded": "unneeded"}
GOAL_LABELS = {"a": "attack", "attack": "attack", "n": "needed", "needed": "needed"}
KIND_ORDER = {"C": 0, "plain": 1, "D": 2}
CANDIDATE_COLUMNS = ["template", "handoff", "receiver", "task", "permission", "meaning", "status", "pilot_label", "tier", "note"]
GOAL_COLUMNS = ["template", "handoff", "task", "goal", "needs", "injection", "label", "note"]
PLAN_COLUMNS = ["template", "handoff", "receiver", "task", "plan", "permissions", "plan_correct", "other_plans", "note"]


def meanings(universe_path):
    universe = json.loads(Path(universe_path).read_text())
    return {f"{entry['service']}:{entry['operation']}": entry["description"] for entry in universe["operations"]}


def template_variants(items):
    grouped = defaultdict(list)
    for item in items:
        if "-b0-" in item["id"]:
            grouped[item["template"]].append(item)
    return grouped


def pilot_labels(template, delegations, workflow, audit_path):
    """pilot audit labels mapped to the new forms, for the carried rows of the development set."""
    if not Path(audit_path).exists():
        return {}
    values = generate.sample_binding(random.Random(f"{template}-0"), delegations["pools"])
    values["channel_ids"] = {values[key]: values[f"{key}_id"] for key in ("channel", "channel2", "other_channel")}
    found = {}
    with open(audit_path, newline="") as handle:
        for row in csv.DictReader(handle):
            if row["template"] == template:
                wildcard = row["permission"].split(":", 2)[2] == "*"
                for text in conversion.pilot_to_new(row["permission"], values, delegations, workflow):
                    found.setdefault(text, {}).setdefault(wildcard, set()).add("needed" if row["final"] == "1" else "not needed")
    return {text: label for text, by_kind in found.items() if (label := carried_label(by_kind))}


def carried_label(by_kind):
    """a label on the pilot's exact permission wins over one on a wildcard mapped to the same permission; conflicting
    labels are not carried, so the row is labelled anew."""
    labels = by_kind.get(False) or by_kind.get(True)
    return next(iter(labels)) if len(labels) == 1 else None


def receiver_text(item):
    receiver = item["request"]["receiver"]
    return f"{receiver['name']} ({'remote' if receiver['remote'] else 'local'})"


def benign_text(variants):
    return next(item for item in variants if item["variant"] == "benign")["request"]["text"]


def candidate_rows(template, variants, glossary, carried):
    pool = list(dict.fromkeys(candidate for item in variants for candidate in answer.candidates(item)))
    pool.sort(key=lambda atom: (KIND_ORDER[atom.kind], str(atom)))
    for atom in pool:
        yield {
            "template": template,
            "handoff": variants[0]["handoff"],
            "receiver": receiver_text(variants[0]),
            "task": benign_text(variants),
            "permission": str(atom),
            "meaning": glossary.get(f"{atom.service}:{atom.operation}", ""),
            "status": "carried" if str(atom) in carried else "new",
            "pilot_label": carried.get(str(atom), ""),
            "tier": "",
            "note": "",
        }


def goal_rows(template, variants):
    goals = {attack["id"]: attack for item in variants for attack in item["attacks"]}
    for goal_id, attack in sorted(goals.items()):
        yield {
            "template": template,
            "handoff": variants[0]["handoff"],
            "task": benign_text(variants),
            "goal": goal_id,
            "needs": " ".join(attack["needs"]),
            "injection": attack["injection"],
            "label": "",
            "note": "",
        }


def plan_rows(template, variants):
    for index, plan in enumerate(variants[0]["plans"]):
        yield {
            "template": template,
            "handoff": variants[0]["handoff"],
            "receiver": receiver_text(variants[0]),
            "task": benign_text(variants),
            "plan": index,
            "permissions": " ".join(plan),
            "plan_correct": "",
            "other_plans": "",
            "note": "",
        }


def write_csv(path, columns, rows):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make_sheets(arguments):
    items = data.read_jsonl(arguments.items)
    delegations = yaml.safe_load(Path(arguments.templates, "delegations.yaml").read_text())
    glossary = meanings(arguments.universe)
    candidates, goals, plans = [], [], []
    for template, variants in template_variants(items).items():
        carried = pilot_labels(template, delegations, variants[0]["workflow"], arguments.audit) if arguments.carry else {}
        candidates += candidate_rows(template, variants, glossary, carried)
        goals += goal_rows(template, variants)
        plans += plan_rows(template, variants)
    out = Path(arguments.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for reviewer in arguments.reviewers.split(","):
        write_csv(out / f"candidates_{reviewer}.csv", CANDIDATE_COLUMNS, candidates)
        write_csv(out / f"goals_{reviewer}.csv", GOAL_COLUMNS, goals)
        write_csv(out / f"plans_{reviewer}.csv", PLAN_COLUMNS, plans)
    new = sum(row["status"] == "new" for row in candidates)
    print(f"{out}: {len(candidates)} candidate rows ({new} new), {len(goals)} goal rows, {len(plans)} plan rows per reviewer")


CHECK_COLUMNS = ["id", "template", "receiver", "task", "required", "plausible", "goals", "correct", "note"]


def carried_check(arguments):
    """a random 10% of tasks whose labels were carried from name binding 0, for one reviewer to confirm."""
    items = [item for item in data.read_jsonl(arguments.items) if "-b0-" not in item["id"]]
    chosen = sorted(random.Random(arguments.seed).sample(items, max(1, round(0.1 * len(items)))), key=lambda item: item["id"])
    rows = []
    for item in chosen:
        required, plausible = answer.tiers(item)
        rows.append({
            "id": item["id"],
            "template": item["template"],
            "receiver": receiver_text(item),
            "task": item["request"]["text"],
            "required": " ".join(map(str, required)),
            "plausible": " ".join(map(str, plausible)),
            "goals": " | ".join(f"{attack['id']}: {' '.join(attack['needs'])}" for attack in item["attacks"]),
            "correct": "",
            "note": "",
        })
    path = Path(arguments.out_dir) / "carried_check.csv"
    write_csv(path, CHECK_COLUMNS, rows)
    print(f"{path}: {len(rows)} of {len(items)} carried tasks")


def read_labels(path, column, vocabulary):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    key = "permission" if column == "tier" else "goal"
    return {(row["template"], row[key]): vocabulary.get(row[column].strip().lower(), "unclear") for row in rows if row[column].strip()}


def agreement(first_path, second_path, column, vocabulary):
    first, second = read_labels(first_path, column, vocabulary), read_labels(second_path, column, vocabulary)
    shared = sorted(set(first) & set(second))
    decided = [key for key in shared if first[key] != "unclear" and second[key] != "unclear"]
    return {
        "pairs": len(shared),
        "decided": len(decided),
        "unclear": len(shared) - len(decided),
        "kappa": stats.cohen_kappa([first[key] for key in decided], [second[key] for key in decided]) if decided else None,
        "disagreements": [{"template": key[0], "item": key[1], "first": first[key], "second": second[key]} for key in shared if first[key] != second[key]],
        "labels": dict(Counter(first[key] for key in decided)),
    }


def compare(arguments):
    names = arguments.reviewers.split(",")
    out = Path(arguments.out_dir)
    report = {}
    for sheet, column, vocabulary in (("candidates", "tier", TIERS), ("goals", "label", GOAL_LABELS)):
        report[sheet] = agreement(out / f"{sheet}_{names[0]}.csv", out / f"{sheet}_{names[1]}.csv", column, vocabulary)
    (out / "agreement.json").write_text(json.dumps(report, indent=2) + "\n")
    for sheet, result in report.items():
        print(f"{sheet}: {result['decided']} decided pairs, kappa {result['kappa']}, {result['unclear']} unclear, {len(result['disagreements'])} disagreements")


def main():
    parser = argparse.ArgumentParser(description="answer-key labeling sheets and reviewer agreement")
    commands = parser.add_subparsers(dest="command", required=True)
    sheets = commands.add_parser("sheets")
    sheets.add_argument("--items", default="data/tasks/dev.jsonl")
    sheets.add_argument("--templates", default="data/templates")
    sheets.add_argument("--universe", default="data/universe.json")
    sheets.add_argument("--audit", default="data/review/audit_final.csv")
    sheets.add_argument("--carry", action="store_true", help="mark candidates the pilot audit already labelled")
    sheets.add_argument("--out-dir", default="data/review/dev")
    sheets.add_argument("--reviewers", default="alvi,joseph")
    agree = commands.add_parser("compare")
    agree.add_argument("--out-dir", default="data/review/dev")
    agree.add_argument("--reviewers", default="alvi,joseph")
    check = commands.add_parser("carried-check")
    check.add_argument("--items", default="data/tasks/dev.jsonl")
    check.add_argument("--out-dir", default="data/review/dev")
    check.add_argument("--seed", type=int, default=0)
    arguments = parser.parse_args()
    {"sheets": make_sheets, "compare": compare, "carried-check": carried_check}[arguments.command](arguments)


if __name__ == "__main__":
    main()
