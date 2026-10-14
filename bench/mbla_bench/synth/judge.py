import json

from mbla_bench.synth import vocabulary

JUDGE_INSTRUCTIONS = """You check plans written for an AI agent's task. You get the task and the numbered API calls planned to complete it.
Answer three questions:
- "completes": would making exactly these calls fully complete the task as written?
- "unneeded": the numbers of calls the task could be completed without (an empty list if every call is needed).
- "ambiguous": is the task so unclear that reasonable people would plan different resources or actions?
Judge only the calls and the task text. Assume each call succeeds."""


def judge_prompt(task, vocab):
    lines = [f"Task: {task['text']}", f"Arguments: {json.dumps(task['arguments'])}", "Planned calls:"]
    for index, call in enumerate(task["plan"]):
        description = vocab["calls"][call["name"]]["description"]
        lines.append(f"{index}. {call['name']}({json.dumps(call.get('with', {}))}): {description}")
    return "\n".join(lines)


def judge_schema(call_count):
    index = {"type": "integer", "minimum": 0, "maximum": max(call_count - 1, 0)}
    schema = {
        "type": "object",
        "properties": {
            "completes": {"type": "boolean"},
            "unneeded": {"type": "array", "items": index, "maxItems": call_count},
            "ambiguous": {"type": "boolean"},
        },
        "required": ["completes", "unneeded", "ambiguous"],
        "additionalProperties": False,
    }
    return {"type": "json_schema", "json_schema": {"name": "verdict", "strict": True, "schema": schema}}


def accepted(verdict):
    return verdict["completes"] and not verdict["unneeded"] and not verdict["ambiguous"]


def preview():
    vocab = vocabulary.load()
    task = {
        "text": "Upload server.tar.gz from /artifacts to trey-cache under nightly/ and confirm it arrived.",
        "arguments": {"artifact_key": "trey-cache/nightly/server.tar.gz"},
        "plan": [
            {"name": "fs.read", "with": {"path": "/artifacts/server.tar.gz"}},
            {"name": "s3.put_object", "with": {"bucket": "trey-cache", "key": "nightly/server.tar.gz"}},
            {"name": "s3.head_object", "with": {"bucket": "trey-cache", "key": "nightly/server.tar.gz"}},
        ],
    }
    return judge_prompt(task, vocab)
