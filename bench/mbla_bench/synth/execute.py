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
    "key": r"[A-Za-z0-9!_.()/-]+",
    "source_key": r"[A-Za-z0-9!_.()/-]+",
    "prefix": r"[A-Za-z0-9!_.()/-]+",
    "doc": NAME,
    "folder": NAME,
    "workspace": r"T[A-F0-9]{8}",
    "channel_id": r"C[A-F0-9]{8}",
    "user": r"U[A-Z0-9]{6,12}",
    "volume": r"/workspace|/workspace/src|/artifacts",
    "host": r"[a-z0-9.-]+\.[a-z]+",
}
GROUNDED = ["owner", "repo", "number", "bucket", "source_bucket", "key", "source_key", "prefix", "doc", "folder", "channel_id", "user", "host"]


def needed_arguments(vocab, name):
    return sorted({placeholder for template in vocab["calls"][name]["needs"] for placeholder in vocabulary.placeholders(template)})


def argument_problems(vocab, call, arguments):
    problems = []
    for name in needed_arguments(vocab, call["name"]):
        value = arguments.get(name)
        if value in (None, ""):
            problems.append(f"{call['name']}: missing {name}")
        elif not re.fullmatch(FORMATS[name], str(value)):
            problems.append(f"{call['name']}: {name}={value!r} is malformed")
    return problems


def grounding_problems(call, arguments, task_text):
    return [f"{call['name']}: {name}={arguments[name]!r} is not named in the task" for name in GROUNDED if name in arguments and str(arguments[name]) not in task_text]


def run_plan(vocab, plan, text, workspace):
    problems, logged = [], []
    for call in plan:
        if call.get("name") not in vocab["calls"]:
            problems.append(f"unknown call {call.get('name')!r}")
            continue
        arguments = {"workspace": workspace, **call.get("with", {})}
        found = argument_problems(vocab, call, arguments) + grounding_problems(call, call.get("with", {}), text)
        problems += found
        if not found:
            logged += vocabulary.call_permissions(vocab, call, arguments)
    return problems, logged


def run(vocab, task):
    """the mock service: runs both plans, logging the permission of every call. a malformed or ungrounded call fails."""
    problems, logged = run_plan(vocab, task["plan"], task["text"], task["workspace"])
    extra_problems, extra_logged = run_plan(vocab, task.get("alternative", []), task["text"], task["workspace"])
    if not 0 <= task.get("check_calls", 0) < max(len(task["plan"]), 1):
        problems.append("check_calls leaves no step after the check")
    return problems + extra_problems, logged + extra_logged
