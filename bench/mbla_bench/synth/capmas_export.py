"""synthetic train and validation in CAPMAS's own split format, for retraining it with its own code. the source is not ours to redistribute."""
import json
from pathlib import Path

from mbla_bench import data, train

OUT = Path("data/external/capmas-src/semantic_scoping/data_splits/MBLA/synth")
SEPARATOR = " Furthermore, "


def needed(item):
    return [permission for permission, tier in train.graded(item).items() if tier == "required"]


def atoms(items):
    return [
        {"prompt": train.describe(item["request"]), "individual_caveat": permission, "individual_description": permission}
        for item in items
        for permission in needed(item)
    ]


def bundles(items):
    return [
        {"prompt": train.describe(item["request"]), "target_caveats": " ".join(needed(item)), "target_description": SEPARATOR.join(needed(item))}
        for item in items
        if needed(item)
    ]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    training = data.read_jsonl("data/tasks/synth_train.jsonl")
    validation = data.read_jsonl("data/tasks/synth_validation.jsonl")
    for name, rows in {"macaroon_train": atoms(training), "macaroon_val": atoms(validation), "macaroon_test": atoms(validation), "bundled_val": bundles(validation), "bundled_test": bundles(validation)}.items():
        (OUT / f"{name}_split.json").write_text(json.dumps(rows))
        print(name, len(rows))


if __name__ == "__main__":
    main()
