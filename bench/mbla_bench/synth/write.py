import json
import random

from mbla_bench import data
from mbla_bench.synth import vocabulary

NAMES = "data/synth/names.yaml"
TASKS_PER_REQUEST = 5

WRITER_INSTRUCTIONS = """You write realistic tasks that one AI agent hands to another, together with the exact API calls the receiving agent must make to finish each task.
Rules:
- Use only the calls listed. Fill every argument a call needs.
- Plan the fewest calls that fully complete the task. Do not add calls the task does not need, such as reading something it never uses.
- Every resource a call touches (repository, issue or pull request number, file path, bucket, object key, document, folder, channel, user) must be named in the task text or in its arguments.
- Use the names given; you may invent issue numbers, file paths and object keys.
- "arguments" are the structured parameters the delegating agent passes along with the text, such as "owner/repo#123", "bucket/key", a document id or a channel name.
- Write the task as the delegating agent would: plain instructions, varied wording and length. Never mention permissions, scopes or API call names.
- Each task in a batch must differ from the others in what it asks for, not only in names."""


def call_line(name, spec):
    arguments = ", ".join(sorted({placeholder for template in spec["needs"] for placeholder in vocabulary.placeholders(template)}))
    features = f"; optional flags: {', '.join(spec['when'])}" if "when" in spec else ""
    return f"- {name}({arguments}): {spec['description']}{features}"


def sample_names(rng, names):
    owner = rng.choice(names["owner"])
    return {
        "owner": owner,
        "repos": rng.sample(names["repo"], 2),
        "labels": rng.sample(names["label"], 2),
        "buckets": [f"{owner}-{suffix}" for suffix in rng.sample(names["bucket_suffix"], 2)],
        "key_prefixes": rng.sample(names["key_prefix"], 2),
        "files": rng.sample(names["file"], 3),
        "docs": rng.sample(names["doc"], 3),
        "folders": rng.sample(names["folder"], 1),
        "channels": rng.sample(names["channel"], 3),
        "users": rng.sample(names["user"], 1),
        "programs": rng.sample(names["program"], 2),
        "region": rng.choice(names["region"]),
    }


def writer_prompt(family, workflow, examples, names, vocab):
    calls = "\n".join(call_line(name, vocab["calls"][name]) for name in family["calls"])
    shown = "\n".join(json.dumps(example) for example in examples) or "(none)"
    return (
        f"Delegation: {workflow['delegator']} hands work to {workflow['receiver']} (operation {workflow['operation']}).\n"
        f"Kind of task: {family['description']}.\n\n"
        f"Calls the receiving agent can make:\n{calls}\n\n"
        f"Names to use: {json.dumps(names)}\n"
        f"Sandbox paths: /workspace (source and scratch), /artifacts (build outputs).\n\n"
        f"Examples of the output format:\n{shown}\n\n"
        f"Write {TASKS_PER_REQUEST} different tasks of this kind."
    )


def writer_schema(family):
    call = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "enum": family["calls"]},
            "with": {"type": "object", "additionalProperties": {"type": "string"}},
        },
        "required": ["name", "with"],
        "additionalProperties": False,
    }
    task = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "arguments": {"type": "object", "additionalProperties": {"type": "string"}},
            "plan": {"type": "array", "items": call, "minItems": 1, "maxItems": 8},
        },
        "required": ["text", "arguments", "plan"],
        "additionalProperties": False,
    }
    schema = {
        "type": "object",
        "properties": {"tasks": {"type": "array", "items": task, "minItems": TASKS_PER_REQUEST, "maxItems": TASKS_PER_REQUEST}},
        "required": ["tasks"],
        "additionalProperties": False,
    }
    return {"type": "json_schema", "json_schema": {"name": "tasks", "strict": True, "schema": schema}}


def preview(family_id="issue-label", seed=0):
    vocab = vocabulary.load()
    families = data.load_yaml("data/synth/families.yaml")
    family = next(entry for entry in families["families"] if entry["id"] == family_id)
    names = sample_names(random.Random(seed), data.load_yaml(NAMES))
    return writer_prompt(family, families["workflows"][family["workflow"]], [], names, vocab)
