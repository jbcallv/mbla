"""dev-set variants for question 5: names the boundclaw adapter's phrasings would find (approximate), and no names."""
import json, re, sys
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(line) for line in open("data/tasks/dev.jsonl")]


def found(named, text):
    service, resource = named.split(":", 1)
    parts = resource.rstrip("/").split("/")
    if service == "github" and parts[2] in ("issues", "pulls"):
        noun = "issue" if parts[2] == "issues" else "pull request"
        repo = re.escape(f"{parts[0]}/{parts[1]}")
        return bool(re.search(rf"{noun} #?{parts[3]} (of|in) {repo}\b", text, re.I))
    if service == "slack":
        return len(parts) > 1 and parts[1] in text
    if service == "storage":
        bucket, key = parts[0], "/".join(parts[1:])
        return f"{bucket}/{key}" in text or bool(re.search(rf"bucket {re.escape(bucket)}, key {re.escape(key)}", text))
    return False  # github contents and actions, docs by title


def extracted(row):
    text = row["request"]["text"]
    return dict(row, request=dict(row["request"], named=[n for n in row["request"]["named"] if found(n, text)]))


def nonamed(row):
    return dict(row, request=dict(row["request"], named=[]))


for name, change in {"extracted": extracted, "nonamed": nonamed}.items():
    (out / f"{name}.jsonl").write_text("".join(json.dumps(change(r)) + "\n" for r in rows))
kept = sum(len(extracted(r)["request"]["named"]) for r in rows)
print("names kept", kept, "of", sum(len(r["request"]["named"]) for r in rows))
