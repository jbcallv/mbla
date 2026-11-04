"""the judge model labels every review row blind, from the labeling guide (D-36). it sees no draft answers."""
import argparse
import csv
import json
from pathlib import Path

import requests

from mbla_bench import review_sample

TIERS = ["required", "plausible", "unneeded"]
GUIDE = "../research/labeling_guide.md"
INSTRUCTIONS = """You are a careful reviewer labeling an answer key. Follow this labeling guide exactly.

{guide}

You get one task and a numbered list of permissions the delegator holds. Label every permission in order. Do not use `unclear`: pick the closest tier."""


def rows_by_template(meaning):
    groups = {}
    for split in ("dev", "test"):
        tiers = review_sample.drafts(split)
        with open(f"data/review/{split}/candidates_joseph.csv", newline="") as sheet:
            rows = [{**row, "split": split} for row in csv.DictReader(sheet)]
        for row in rows + review_sample.goal_rows(split, tiers, meaning):
            groups.setdefault((split, row["template"]), []).append(row)
    return groups


def schema(count):
    items = {"type": "string", "enum": TIERS}
    labels = {"type": "array", "items": items, "minItems": count, "maxItems": count}
    return {"type": "json_schema", "json_schema": {"name": "labels", "strict": True, "schema": {"type": "object", "properties": {"labels": labels}, "required": ["labels"], "additionalProperties": False}}}


def prompt(rows):
    first = rows[0]
    lines = [f"Task: {first['task']}", f"Receiver: {first['receiver']}", "Permissions:"]
    lines += [f"{index}. {row['permission']} ({row['meaning']})" for index, row in enumerate(rows)]
    return "\n".join(lines)


def ask(endpoint, model, guide, rows):
    body = {
        "model": model, "temperature": 0, "seed": 0, "max_tokens": 1500, "response_format": schema(len(rows)),
        "messages": [{"role": "system", "content": INSTRUCTIONS.format(guide=guide)}, {"role": "user", "content": prompt(rows)}],
    }
    response = requests.post(f"{endpoint}/chat/completions", json=body, timeout=300)
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])["labels"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()
    guide = Path(GUIDE).read_text()
    columns = ["split", "template", "permission", "label"]
    with open(arguments.out, "w", newline="") as sheet:
        writer = csv.DictWriter(sheet, columns)
        writer.writeheader()
        for (split, template), rows in rows_by_template(review_sample.meanings()).items():
            for row, label in zip(rows, ask(arguments.endpoint, arguments.model, guide, rows)):
                writer.writerow({"split": split, "template": template, "permission": row["permission"], "label": label})
            print(split, template, len(rows), flush=True)


if __name__ == "__main__":
    main()
