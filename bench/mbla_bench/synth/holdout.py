import argparse
import random
from collections import defaultdict

from mbla_bench import data

FAMILIES = "data/synth/families.yaml"
HELD_OUT = {"BC-1": 3, "BC-2": 3, "BC-3": 2}
SEED = "D-21"


def held_out(families):
    by_workflow = defaultdict(list)
    for family in families:
        by_workflow[family["workflow"]].append(family["id"])
    rng = random.Random(SEED)
    return sorted(family for workflow, count in sorted(HELD_OUT.items()) for family in rng.sample(sorted(by_workflow[workflow]), count))


def main():
    argparse.ArgumentParser(description="draw the held-out families (fixed seed, stratified by workflow)").parse_args()
    families = data.load_yaml(FAMILIES)["families"]
    counts = defaultdict(int)
    for family in families:
        counts[family["workflow"]] += 1
    print(f"{len(families)} families: {dict(counts)}")
    print("held out:", ", ".join(held_out(families)))


if __name__ == "__main__":
    main()
