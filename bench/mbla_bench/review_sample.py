"""one blind review sheet: a human labels a sample of rows, for checking the judge model against a person (D-36)."""
import csv
import json
import random
from pathlib import Path

from mbla_bench import answer, data

SIZE = 120
SEED = 36
SHEET_COLUMNS = ["row", "task", "receiver", "permission", "meaning", "answer", "note"]
KEY_COLUMNS = ["row", "split", "template", "handoff", "source", "draft"]


def meanings():
    universe = json.loads(Path("data/universe.json").read_text())
    return {f"{entry['service']}:{entry['operation']}": entry["description"] for entry in universe["operations"]}


def drafts(split):
    tiers = {}
    for item in data.read_jsonl(f"data/tasks/{split}.jsonl"):
        if "-b0-" in item["id"]:
            required, plausible = answer.tiers(item)
            found = tiers.setdefault(item["template"], {})
            found.update({str(atom): "plausible" for atom in plausible})
            found.update({str(atom): "required" for atom in required})
    return tiers


def candidate_rows(split, tiers):
    with open(f"data/review/{split}/candidates_joseph.csv", newline="") as sheet:
        rows = [row for row in csv.DictReader(sheet) if row["status"] == "new"]
    return [{**row, "split": split, "source": "candidate", "draft": tiers[row["template"]].get(row["permission"], "unneeded")} for row in rows]


def goal_rows(split, tiers, meaning):
    """attack permissions missing from the candidate rows, asked the same question."""
    with open(f"data/review/{split}/candidates_joseph.csv", newline="") as sheet:
        rows = list(csv.DictReader(sheet))
    offered = {(row["template"], row["permission"]) for row in rows}
    receivers = {row["template"]: row["receiver"] for row in rows}
    found = {}
    with open(f"data/review/{split}/goals_joseph.csv", newline="") as sheet:
        for goal in csv.DictReader(sheet):
            for permission in goal["needs"].split():
                if (goal["template"], permission) not in offered:
                    service, operation = permission.split(":")[:2]
                    found[(goal["template"], permission)] = {
                        "split": split, "template": goal["template"], "handoff": goal["handoff"], "task": goal["task"], "receiver": receivers[goal["template"]],
                        "permission": permission, "meaning": meaning.get(f"{service}:{operation}", ""), "source": "goal", "draft": tiers[goal["template"]].get(permission, "unneeded"),
                    }
    return list(found.values())


def spread(rows, count, rng):
    """an even random draw across templates: within a template, rows take evenly spaced random positions."""
    by_template = {}
    for row in rows:
        by_template.setdefault(row["template"], []).append(row)
    keyed = []
    for group in by_template.values():
        rng.shuffle(group)
        offset = rng.random()
        keyed += [((position + offset) / len(group), row["permission"], row) for position, row in enumerate(group)]
    return [row for _, _, row in sorted(keyed, key=lambda entry: entry[:2])[:count]]


def main():
    rng = random.Random(SEED)
    meaning = meanings()
    candidates, goals = [], []
    for split in ("dev", "test"):
        tiers = drafts(split)
        candidates += candidate_rows(split, tiers)
        goals += goal_rows(split, tiers, meaning)
    needed = [row for row in candidates if row["draft"] != "unneeded"]
    unneeded = [row for row in candidates if row["draft"] == "unneeded"]
    chosen = needed + spread(unneeded, SIZE - len(needed), rng) + goals
    chosen.sort(key=lambda row: (row["task"], row["permission"]))
    for number, row in enumerate(chosen, 1):
        row["row"] = number
    write("../share/review_sheet.csv", SHEET_COLUMNS, chosen)
    write("data/review/sample/key.csv", KEY_COLUMNS, chosen)
    print(len(chosen), "rows:", len(needed), "drafted needed,", SIZE - len(needed), "drafted unneeded,", len(goals), "attack permissions;", len(candidates), "candidates in all")


def write(path, columns, rows):
    with open(path, "w", newline="") as sheet:
        writer = csv.DictWriter(sheet, columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
