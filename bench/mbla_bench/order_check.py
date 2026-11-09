"""D-64 diagnostic, development set only: one chat helper answered in the deployed order (plausible first, as mbla
sends the schema) and in the trained order (required first). rows are written in the benchmark's raw format, so the
normal report scores them. the deployed-order rows also check this client against the benchmark's own runs."""

import argparse
import json
from pathlib import Path

from mbla_bench import adaptive, answer, data


def row(item, method, permissions, raw):
    selected = adaptive.row_of(raw, permissions)
    chosen = {"required": [], "plausible": []} if selected.get("parse_failed") else json.loads(raw)
    scores = [1.0 if index in chosen["required"] else 0.5 if index in chosen["plausible"] else 0.0 for index in range(len(permissions))]
    return {"item": item["id"], "method": method, "input": "full", "seed": 0, "candidates": permissions, "scores": scores, "thresholds": [0.8, 0.2], "error": "", "hardware": "shared GPU (other users' jobs present): latency not used, see the latency experiment", **selected, "parse_failed": bool(selected.get("parse_failed"))}


def main():
    parser = argparse.ArgumentParser(description="D-64: deployed vs trained answer order, development set only")
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--served", required=True)
    parser.add_argument("--method", default="qwen3-4b-tuned-s2")
    arguments = parser.parse_args()
    out = Path("results/raw/dev-order")
    out.mkdir(parents=True, exist_ok=True)
    for label, go_order in (("deployed-order", True), ("required-first", False)):
        method = f"{arguments.method}-{label}"
        rows = []
        for item in data.read_jsonl("data/tasks/dev.jsonl"):
            permissions = [str(candidate) for candidate in answer.candidates(item)]
            rows.append(row(item, method, permissions, adaptive.deployed_answer(arguments.endpoint, arguments.served, item["request"], permissions, go_order)))
        (out / f"{method}__full__s0.jsonl").write_text("".join(json.dumps(entry) + "\n" for entry in rows))
        print(method, len(rows), "rows")


if __name__ == "__main__":
    main()
