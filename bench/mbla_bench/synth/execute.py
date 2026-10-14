import re

from mbla_bench.synth import vocabulary

NAME = r"[a-z0-9][a-z0-9-]{0,38}"
FORMATS = {
    "owner": NAME,
    "repo": r"[a-z0-9][a-z0-9._-]{0,99}",
    "number": r"[1-9][0-9]{0,5}",
    "path": r"[A-Za-z0-9._/-]+",
    "bucket": r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]",
    "source_bucket": r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]",
    "key": r"[A-Za-z0-9!_.*'()/-]+",
    "source_key": r"[A-Za-z0-9!_.*'()/-]+",
    "prefix": r"[A-Za-z0-9!_.*'()/-]+",
    "region": r"[a-z]{2}-[a-z]+-[1-9]",
    "doc": NAME,
    "folder": NAME,
    "channel": r"[a-z0-9][a-z0-9_-]{0,79}",
    "user": r"U[A-Z0-9]{6,12}",
    "program": r"/[A-Za-z0-9._/-]+",
}
SANDBOX_PATH = r"/(workspace|artifacts|tmp)(/[A-Za-z0-9._-]+)*"
GROUNDED = ["owner", "repo", "number", "bucket", "source_bucket", "key", "source_key", "prefix", "doc", "folder", "channel", "user"]


def needed_arguments(vocab, name):
    spec = vocab["calls"][name]
    templates = spec["needs"] + ([vocab["hosts"][spec["host"]]] if "host" in spec else [])
    return sorted({placeholder for template in templates for placeholder in vocabulary.placeholders(template)})


def argument_problems(vocab, call, arguments):
    problems = []
    for name in needed_arguments(vocab, call["name"]):
        value = arguments.get(name)
        if value in (None, ""):
            problems.append(f"{call['name']}: missing {name}")
            continue
        pattern = SANDBOX_PATH if name == "path" and call["name"].startswith("fs.") else FORMATS[name]
        if not re.fullmatch(pattern, str(value)):
            problems.append(f"{call['name']}: {name}={value!r} is malformed")
    return problems


def grounding_problems(call, arguments, task_text, task_arguments):
    mentioned = task_text + " " + " ".join(str(value) for value in task_arguments.values())
    return [
        f"{call['name']}: {name}={arguments[name]!r} is not named in the task"
        for name in GROUNDED
        if name in arguments and str(arguments[name]) not in mentioned
    ]


def run(vocab, task):
    problems, logged = [], []
    for call in task["plan"]:
        if call.get("name") not in vocab["calls"]:
            problems.append(f"unknown call {call.get('name')!r}")
            continue
        arguments = {"region": task.get("region", "us-east-1"), **call.get("with", {})}
        found = argument_problems(vocab, call, arguments) + grounding_problems(call, call.get("with", {}), task["text"], task["arguments"])
        problems += found
        if not found:
            logged += vocabulary.call_permissions(vocab, call, arguments)
    return problems, logged
