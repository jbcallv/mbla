"""alignment between the judge model and the humans (D-36): the pilot labels pick the judge; the review sheet tests it."""
import argparse
import csv

import numpy as np

SKIPPED = {"27", "28", "69", "70", "71", "72", "73", "74"}
WIDER = set("6 7 10 12 18 22 32 33 38 41 53 60 67 93 123".split())
RULED = {**{row: "unneeded" for row in WIDER | set("5 9 40 78 23 119".split())}, "34": "required", "68": "required", "124": "required", "57": "plausible"}
RESAMPLES = 5000


def kappa(first, second):
    agree = (first == second).mean()
    chance = sum((first == label).mean() * (second == label).mean() for label in set(first) | set(second))
    return (agree - chance) / (1 - chance) if chance < 1 else 1.0


def interval(first, second, seed=0):
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(first), (RESAMPLES, len(first)))
    return np.percentile([kappa(first[draw], second[draw]) for draw in draws], [2.5, 97.5])


def report(name, human, judge):
    human, judge = np.array(human), np.array(judge)
    low, high = interval(human, judge)
    print(f"{name}: {len(human)} rows, agreement {(human == judge).mean():.3f}, kappa {kappa(human, judge):.3f} (95% {low:.3f}-{high:.3f})")
    for label in sorted(set(human) | set(judge)):
        print(f"  human {label:10s}", {other: int(((human == label) & (judge == other)).sum()) for other in sorted(set(judge))})


def read(path):
    with open(path, newline="") as sheet:
        return list(csv.DictReader(sheet))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", required=True)
    parser.add_argument("--pilot-only", action="store_true")
    arguments = parser.parse_args()
    labels = {(row["template"], row["permission"]): row["label"] for row in read(arguments.judge)}
    pilot = [row for split in ("dev", "test") for row in read(f"data/review/{split}/candidates_joseph.csv") if row["status"] == "carried"]
    report("pilot labels (needed vs not)", [row["pilot_label"] for row in pilot], ["needed" if labels[(row["template"], row["permission"])] != "unneeded" else "not needed" for row in pilot])
    if arguments.pilot_only:
        return
    key = {row["row"]: row for row in read("data/review/sample/key.csv")}
    rows = [row for row in read("data/review/sample/joseph.csv") if row["row"] not in SKIPPED]
    human = [RULED.get(row["row"], row["answer"]) for row in rows]
    judge = [labels[(key[row["row"]]["template"], row["permission"])] for row in rows]
    report("review sheet", human, judge)
    needed = [index for index, label in enumerate(human) if label != "unneeded"]
    report("review sheet, rows the human called needed", [human[index] for index in needed], [judge[index] for index in needed])
    for row, wanted, got in zip(rows, human, judge):
        if wanted != got:
            print(" ", row["row"], key[row["row"]]["template"], "human", wanted, "judge", got, row["permission"])


if __name__ == "__main__":
    main()
