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

You get one task, every permission offered for it, and the one permission to label. Do not use `unclear`: pick the closest tier."""


def rows_by_template(meaning):
    groups = {}
    for split in ("dev", "test"):
        tiers = review_sample.drafts(split)
        with open(f"data/review/{split}/candidates_joseph.csv", newline="") as sheet:
            rows = [{**row, "split": split} for row in csv.DictReader(sheet)]
        for row in rows + review_sample.goal_rows(split, tiers, meaning):
            groups.setdefault((split, row["template"]), []).append(row)
    return groups


SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "label", "strict": True,
        "schema": {
            "type": "object",
            "properties": {"reason": {"type": "string", "maxLength": 300}, "label": {"type": "string", "enum": TIERS}},
            "required": ["reason", "label"], "additionalProperties": False,
        },
    },
}


def prompt(rows, index):
    first = rows[0]
    lines = [f"Task: {first['task']}", f"Receiver: {first['receiver']}", "All permissions offered:"]
    lines += [f"- {row['permission']} ({row['meaning']})" for row in rows]
    lines += ["", f"Label only this one: {rows[index]['permission']}", "First say in one sentence what it allows and whether a narrower offered permission already covers the need. Then give the label."]
    return "\n".join(lines)


def ask(endpoint, model, guide, rows, index):
    body = {
        "model": model, "temperature": 0, "seed": 0, "max_tokens": 300, "response_format": SCHEMA,
        "messages": [{"role": "system", "content": INSTRUCTIONS.format(guide=guide)}, {"role": "user", "content": prompt(rows, index)}],
    }
    response = requests.post(f"{endpoint}/chat/completions", json=body, timeout=300)
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--pilot-only", action="store_true")
    arguments = parser.parse_args()
    guide = Path(GUIDE).read_text()
    columns = ["split", "template", "permission", "label", "reason"]
    with open(arguments.out, "w", newline="") as sheet:
        writer = csv.DictWriter(sheet, columns)
        writer.writeheader()
        for (split, template), rows in rows_by_template(review_sample.meanings()).items():
            for index, row in enumerate(rows):
                if arguments.pilot_only and row.get("status") != "carried":
                    continue
                answer = ask(arguments.endpoint, arguments.model, guide, rows, index)
                writer.writerow({"split": split, "template": template, "permission": row["permission"], "label": answer["label"], "reason": answer["reason"]})
            print(split, template, len(rows), flush=True)


if __name__ == "__main__":
    main()
