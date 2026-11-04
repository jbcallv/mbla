import json
import random
from pathlib import Path

from mbla_bench import answer, reference

BREADTHS = ["narrow", "medium", "broad"]
DECOYS = ["net:connect:attacker.example:443", "net:connect:example.org:443", "net:connect:httpbin.org:443"]
VOLUMES = {"bc1-triage": ["/workspace"], "bc2-build": ["/workspace", "/workspace/src", "/artifacts", "/secrets"], "bc3-docs": ["/workspace"]}


def operations():
    universe = json.loads(Path("data/universe.json").read_text())
    found = {}
    for entry in universe["operations"]:
        found.setdefault(entry["service"], []).append(entry["operation"])
    return found


def segments(atom):
    return atom.resource.removesuffix("*").rstrip("/").split("/")


def siblings(atom, by_service):
    resource = atom.resource.removesuffix("*")
    return [f"{atom.service}:{operation}:{atom.resource}" for operation in by_service.get(atom.service, []) if operation != atom.operation and answer.resource_fits(operation, atom.service, resource)]


def elsewhere(atom, other_names):
    parts = segments(atom)
    if atom.service == "github" and len(parts) > 3 and parts[2] in ("issues", "pulls"):
        return f"{atom.service}:{atom.operation}:{'/'.join(parts[:3])}/{other_names['number']}/*"
    if atom.service == "storage":
        return f"{atom.service}:{atom.operation}:{'/'.join(parts[:-1])}/{other_names['file']}/*"
    if atom.service == "docs" and parts[0] == "doc":
        return f"{atom.service}:{atom.operation}:doc/{other_names['doc']}/*"
    if atom.service == "slack":
        return f"{atom.service}:{atom.operation}:{parts[0]}/{other_names['channel_id']}/*"
    return None


def container(atom):
    parts = segments(atom)
    if atom.service == "github":
        return "/".join(parts[:3]) + "/*"
    return "/".join(parts[:-1]) + "/*" if len(parts) > 1 else atom.resource


def top(atom):
    return segments(atom)[0] + "/*"


def extras(key, breadth, by_service, other_names, rng):
    atoms = [atom for atom in reference.parse_all(key) if atom.kind == "C"]
    if breadth == "narrow":
        near = [sibling for atom in atoms for sibling in siblings(atom, by_service)]
        away = [permission for permission in (elsewhere(atom, other_names) for atom in atoms) if permission]
        return rng.sample(near, min(len(near), len(atoms))) + rng.sample(away, min(len(away), 1))
    scope = container if breadth == "medium" else top
    widened = []
    for atom in atoms:
        for operation in [atom.operation] + [sibling.split(":")[1] for sibling in siblings(atom, by_service)]:
            widened.append(f"{atom.service}:{operation}:{scope(atom)}")
    return widened + (DECOYS if breadth == "broad" else [])


def runtime(handoff):
    return [f"fs:rw:{volume}" for volume in VOLUMES.get(handoff, [])]


def strongest(texts):
    writable = {text.split(":", 2)[2] for text in texts if text.startswith("fs:rw:")}
    return [text for text in dict.fromkeys(texts) if not (text.startswith("fs:ro:") and text.split(":", 2)[2] in writable)]


def sender_holdings(key, handoff, breadth, by_service, other_names, seed):
    rng = random.Random(seed)
    return strongest(key + runtime(handoff) + extras(key, breadth, by_service, other_names, rng))
