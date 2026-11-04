"""exploratory only: development tasks with extra context lines added after the task line, for an input comparison.
not part of the final methodology; run on unreviewed answer keys."""
import json
import sys
from pathlib import Path


def receiver_text(receiver):
    return f"{receiver['name']} ({'remote' if receiver['remote'] else 'local'})"


def extended(item, with_history):
    request = item["request"]
    lines = [request["text"], f"operation: {request['protocol']} {request['operation']}", f"receiver: {receiver_text(request['receiver'])}"]
    lines += [f"history: {step}" for step in request["history"]] if with_history else []
    request["text"] = "\n".join(lines)
    return item


def write_variant(source, target, with_history):
    items = [extended(json.loads(line), with_history) for line in Path(source).read_text().splitlines()]
    Path(target).write_text("".join(json.dumps(item) + "\n" for item in items))


if __name__ == "__main__":
    out = Path(sys.argv[1])
    write_variant("data/tasks/dev.jsonl", out / "dev_op_receiver.jsonl", False)
    write_variant("data/tasks/dev.jsonl", out / "dev_op_receiver_history.jsonl", True)
