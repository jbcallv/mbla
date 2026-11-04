import json
import random

from mbla_bench import data, generate
from mbla_bench.synth import execute, vocabulary

NAMES = "data/synth/names.yaml"
TASKS_PER_REQUEST = 5

WRITER_INSTRUCTIONS = """You write realistic tasks that one AI agent hands to another, together with the exact API calls the receiving agent must make to finish each task.
Rules:
- Use only the calls listed. Fill every argument a call needs.
- "plan" is the fewest calls that fully complete the task. Do not add calls the task does not need.
- "alternative" is another valid set of calls for the same task that a competent engineer would really use, or an empty list if there is none.
- A later step may depend on what an earlier call finds ("label it if it is a duplicate"). Then "check_calls" is the number of leading calls that decide the condition. Otherwise it is 0.
- Every resource a call touches (repository, issue or pull request number, file path, bucket, object key, document, folder, channel id, user, website) must appear in the task text, spelled exactly.
- The reverse also holds: the task must not ask for anything the plan does not do. If the task says to post, share, notify, upload or read something, the plan has a call for it. Local work on a folder (running tests, builds, linters) needs only that folder's call, and the result goes back to the delegator.
- A channel appears in the text as <#ID|name>. The call argument channel_id is the ID.
- Write repositories as owner/repo and objects as bucket/key in full, for example "issue 42 in alpine/frontend" and "alpine-staging/nightly/server.tar.gz". A call's key is the whole path after the bucket.
- Use the names given; you may invent issue numbers, file paths and object keys.
- Folders are /workspace, /workspace/src and /artifacts. A program that reads the source needs the folder /workspace/src; a program that writes output needs /artifacts.
- S3 uploads overwrite an existing object, so do not delete first unless the task says to delete.
- Write the task as the delegating agent would: plain instructions, varied wording and length. Never mention permissions, scopes or API call names.
- Each task in a batch must differ from the others in what it asks for, not only in names."""


def call_line(name, spec):
    arguments = ", ".join(sorted({placeholder for template in spec["needs"] for placeholder in vocabulary.placeholders(template) if placeholder != "workspace"}))
    return f"- {name}({arguments}): {spec['description']}"


def sample_names(rng, names):
    owner = rng.choice(names["owner"])
    channels = rng.sample(names["channel"], 3)
    return {
        "owner": owner,
        "repos": rng.sample(names["repo"], 2),
        "labels": rng.sample(names["label"], 2),
        "buckets": [f"{owner}-{suffix}" for suffix in rng.sample(names["bucket_suffix"], 2)],
        "key_prefixes": rng.sample(names["key_prefix"], 2),
        "files": rng.sample(names["file"], 3),
        "docs": rng.sample(names["doc"], 3),
        "folders": rng.sample(names["folder"], 1),
        "channels": [{"name": channel, "id": generate.slack_id("C", f"{owner}/{channel}")} for channel in channels],
        "users": rng.sample(names["user"], 1),
        "websites": rng.sample(names["host"], 2),
    }


def writer_prompt(family, handoff, names, vocab):
    calls = "\n".join(call_line(name, vocab["calls"][name]) for name in family["calls"])
    return (
        f"Delegation: {handoff['delegator']} hands work to {handoff['receiver']} (operation {handoff['operation']}).\n"
        f"Kind of task: {family['description']}.\n\n"
        f"Calls the receiving agent can make:\n{calls}\n\n"
        f"Names to use: {json.dumps(names)}\n\n"
        f"Write {TASKS_PER_REQUEST} different tasks of this kind."
    )


def call_schema(name, vocab):
    arguments = [argument for argument in execute.needed_arguments(vocab, name) if argument != "workspace"]
    return {
        "type": "object",
        "properties": {
            "name": {"const": name},
            "with": {"type": "object", "properties": {argument: {"type": "string", "pattern": f"^({execute.FORMATS[argument]})$"} for argument in arguments}, "required": arguments, "additionalProperties": False},
        },
        "required": ["name", "with"],
        "additionalProperties": False,
    }


def writer_schema(family, vocab):
    call = {"anyOf": [call_schema(name, vocab) for name in family["calls"]]}
    task = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "plan": {"type": "array", "items": call, "minItems": 1, "maxItems": 8},
            "alternative": {"type": "array", "items": call, "maxItems": 8},
            "check_calls": {"type": "integer", "minimum": 0, "maximum": 7},
        },
        "required": ["text", "plan", "alternative", "check_calls"],
        "additionalProperties": False,
    }
    schema = {
        "type": "object",
        "properties": {"tasks": {"type": "array", "items": task, "minItems": TASKS_PER_REQUEST, "maxItems": TASKS_PER_REQUEST}},
        "required": ["tasks"],
        "additionalProperties": False,
    }
    return {"type": "json_schema", "json_schema": {"name": "tasks", "strict": True, "schema": schema}}


def handoff_of(family, families):
    name = family.get("handoff") or families["workflows"][family["workflow"]]["handoff"]
    return name, families["handoffs"][name]


def other_names(rng, names, used):
    return {
        "number": rng.randint(1000, 9999),
        "file": rng.choice([file for file in names["file"] if file not in used["files"]]),
        "doc": rng.choice([doc for doc in names["doc"] if doc not in used["docs"]]),
        "channel_id": generate.slack_id("C", f"{used['owner']}/{used['channels'][-1]['name']}"),
    }


def tasks_from(response, family, names, chosen, seed):
    tasks = []
    for index, task in enumerate(response["tasks"]):
        if task["alternative"] == task["plan"]:
            task["alternative"] = []
        tasks.append({**task, "id": f"{family['id']}-{seed}-{index}", "family": family["id"], "workspace": generate.slack_id("T", chosen["owner"]), "other_names": other_names(random.Random(f"{seed}-{index}"), names, chosen)})
    return tasks


def preview(family_id="issue-label", seed=0):
    vocab = vocabulary.load()
    families = data.load_yaml("data/synth/families.yaml")
    family = next(entry for entry in families["families"] if entry["id"] == family_id)
    names = sample_names(random.Random(seed), data.load_yaml(NAMES))
    return writer_prompt(family, handoff_of(family, families)[1], names, vocab)
