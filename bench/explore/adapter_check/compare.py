"""compare variants of the dev set on the hosted helper: coverage, excess C, attack reach, and identical answers."""
import json, sys
from pathlib import Path

from mbla_bench import answer, report

folder = Path(sys.argv[1])
variants = sys.argv[2:]


def normal(text):
    return text.replace("%7Edefault", "~default").replace("/*", "*")


def answers(rows):
    return {row["item"]: {normal(c): s for c, s in zip(row["candidates"], row["scores"]) if s > 0} for row in rows}


base = None
for variant in variants:
    items = {json.loads(line)["id"]: json.loads(line) for line in open(folder / f"{variant}.jsonl")}
    rows = [json.loads(line) for line in open(folder / f"pred_{variant}.jsonl")]
    keys = {item_id: answer.tiers(item)[0] for item_id, item in items.items()}
    frame = report.task_frame(items, rows, keys)
    chosen = answers(rows)
    base = base or chosen
    same = sum(chosen[i] == base[i] for i in chosen) / len(chosen)
    injected = frame[frame["injected"]]
    errors = sum(bool(row["error"]) or row["parse_failed"] for row in rows)
    print(f"{variant:10s} n={len(frame)} coverage={frame['covered_A-bounded_k3'].mean():.3f} excessC={frame['excess_C'].mean():.3f} "
          f"reachA_injected={injected['reach_A-bounded_k3'].mean():.3f} same_answer={same:.3f} errors={errors}")
