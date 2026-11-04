import argparse
import json
import re
from pathlib import Path

from mbla_bench import data

VOCABULARY = Path("data/synth/vocabulary.yaml")
AWS_REFERENCE = Path("data/external/catalogs/aws/s3.json")
PLACEHOLDER = re.compile(r"\{(\w+)\}")
AWS_ACTION = re.compile(r"s3:([A-Z]\w+)")


def load():
    return data.load_yaml(VOCABULARY)


def placeholders(text):
    return PLACEHOLDER.findall(text)


def fill(template, values):
    return PLACEHOLDER.sub(lambda match: str(values[match.group(1)]), template)


def call_permissions(vocabulary, call, arguments):
    return [fill(permission, arguments) for permission in vocabulary["calls"][call["name"]]["needs"]]


def aws_actions_by_operation():
    reference = json.loads(AWS_REFERENCE.read_text())
    return {operation["Name"]: {action["Name"] for action in operation.get("AuthorizedActions", []) if action["Service"] == "s3"} for operation in reference["Operations"]}


def aws_problems(vocabulary):
    authorized = aws_actions_by_operation()
    problems = []
    for name, spec in vocabulary["calls"].items():
        if not name.startswith("s3."):
            continue
        operations = [operation.strip() for operation in spec["source"].split("->")[0].split(",")]
        allowed = set().union(*(authorized.get(operation, set()) for operation in operations))
        problems += [f"{name}: {operation} is not an S3 operation in the AWS reference" for operation in operations if operation not in authorized]
        problems += [f"{name}: s3:{action} does not authorize {', '.join(operations)}" for action in set(AWS_ACTION.findall(spec["source"])) if action not in allowed]
    return problems


def main():
    argparse.ArgumentParser(description="check the synthetic-data vocabulary against the provider references").parse_args()
    vocabulary = load()
    problems = aws_problems(vocabulary)
    print(f"{len(vocabulary['calls'])} calls; {len(problems)} problems")
    for problem in problems:
        print(" ", problem)
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
