import json
from pathlib import Path

import yaml


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def items_by_id(*paths):
    return {item["id"]: item for path in paths for item in read_jsonl(path)}


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def prediction_files(experiment_dir):
    return sorted(Path(experiment_dir).glob("*.jsonl"))


def load_predictions(experiment_dir):
    rows = []
    for path in prediction_files(experiment_dir):
        rows += read_jsonl(path)
    return rows
