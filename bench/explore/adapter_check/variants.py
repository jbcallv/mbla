"""dev-set variants for the boundclaw adapter questions: storage without trailing slash, escaped ref, sorted names."""
import json, sys
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(line) for line in open("data/tasks/dev.jsonl")]


def rewrite(value, change):
    if isinstance(value, str):
        return change(value)
    if isinstance(value, list):
        return [rewrite(v, change) for v in value]
    if isinstance(value, dict):
        return {k: rewrite(v, change) for k, v in value.items()}
    return value


def noslash(row):
    named = [n[len("storage:"):].rstrip("/") for n in row["request"]["named"] if n.startswith("storage:")]
    def change(text):
        for name in named:
            text = text.replace(f":{name}/*", f":{name}*")
        return text
    row = {k: (v if k in ("request",) else rewrite(v, change)) for k, v in row.items()}
    row["request"] = dict(row["request"], manifest=rewrite(row["request"]["manifest"], change),
                          named=[n.rstrip("/") if n.startswith("storage:") else n for n in row["request"]["named"]])
    return row


def escaped(row):
    return rewrite(row, lambda text: text.replace("~default", "%7Edefault") if not text.startswith(("Fetch", "Read")) and ":" in text else text)


def sorted_named(row):
    return dict(row, request=dict(row["request"], named=sorted(row["request"]["named"])))


for name, change in {"base": lambda r: r, "noslash": noslash, "escaped": escaped, "sorted": sorted_named}.items():
    (out / f"{name}.jsonl").write_text("".join(json.dumps(change(json.loads(json.dumps(r)))) + "\n" for r in rows))
