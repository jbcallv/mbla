"""gemma labels every row of the 93-task sheet blind, with the frozen labeling prompt (D-41, D-47)."""
import argparse
import csv
from pathlib import Path

import requests

from mbla_bench import label_judge
from mbla_bench.synth import audit

OUT = "data/review/synth/judge_gemma.csv"


def label(endpoint, model, guide, rows, index):
    try:
        return label_judge.ask(endpoint, model, guide, rows, index)
    except (requests.RequestException, ValueError, KeyError) as error:
        print(rows[index]["row"], "failed:", error, flush=True)
        return {"label": "", "reason": ""}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", default=OUT)
    arguments = parser.parse_args()
    guide = Path(label_judge.GUIDE).read_text()
    with open(audit.SHEET, newline="") as sheet:
        tasks = audit.by_task(csv.DictReader(sheet))
    with open(arguments.out, "w", newline="") as out:
        writer = csv.DictWriter(out, ["row", "answer", "reason"])
        writer.writeheader()
        for number, rows in tasks.items():
            for index, row in enumerate(rows):
                found = label(arguments.endpoint, arguments.model, guide, rows, index)
                writer.writerow({"row": row["row"], "answer": found["label"], "reason": found["reason"]})
            out.flush()
            print(number, len(rows), flush=True)


if __name__ == "__main__":
    main()
