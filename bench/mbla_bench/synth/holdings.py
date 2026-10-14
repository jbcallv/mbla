import random

from mbla_bench import reference
from mbla_bench.synth import vocabulary

BREADTHS = ["narrow", "medium", "broad"]
RUNTIME = ["fs:w:/workspace", "exec:run:/usr/bin/python3"]
BROAD_SANDBOX = ["net:connect:*", "fs:r:*", "exec:run:*"]


def resource_template(template):
    return template.split(":", 2)[2]


def operations_by_shape(vocab):
    shapes = {}
    for spec in vocab["calls"].values():
        for template in spec["needs"] + [permission for extra in spec.get("when", {}).values() for permission in extra]:
            service, operation, _ = template.split(":", 2)
            if service in ("fs", "exec"):
                continue
            shapes.setdefault((service, resource_template(template)), set()).add(operation)
    return {key: sorted(operations) for key, operations in shapes.items()}


def fits(shape, resource):
    return ("#" in shape) == ("#" in resource) and shape.count("/") <= resource.count("/")


def shape_of(atom, shapes):
    fitting = [shape for (service, shape), operations in shapes.items() if service == atom.service and atom.operation in operations and fits(shape, atom.resource)]
    return max(fitting, key=lambda shape: shape.count("/"), default=None)


def siblings(atom, shapes):
    shape = shape_of(atom, shapes)
    if shape is None:
        return []
    return [f"{atom.service}:{operation}:{atom.resource}" for operation in shapes[(atom.service, shape)] if operation != atom.operation]


def elsewhere(atom, other_names):
    if atom.service == "github" and "#" in atom.resource:
        return f"{atom.service}:{atom.operation}:{atom.resource.split('#')[0]}#{other_names['number']}"
    if atom.service == "storage" and "/" in atom.resource:
        return f"{atom.service}:{atom.operation}:{atom.resource.rsplit('/', 1)[0]}/{other_names['file']}"
    if atom.service in ("docs", "slack") and "/" not in atom.resource:
        return f"{atom.service}:{atom.operation}:{other_names[atom.service]}"
    return None


def container(atom):
    resource = atom.resource.split("#")[0] if "#" in atom.resource else atom.resource.rsplit("/", 1)[0] if "/" in atom.resource else "*"
    if atom.service == "github" and resource.count("/") > 1:
        resource = "/".join(resource.split("/")[:2])
    return resource if resource == "*" else resource + ("" if atom.service == "github" else "/*")


def top(atom):
    return atom.resource.split("/")[0] + "/*" if "/" in atom.resource else "*"


def capability(key):
    return [atom for atom in reference.parse_all(key) if atom.kind == "C"]


def extras(key, breadth, shapes, other_names, rng):
    atoms = capability(key)
    if breadth == "narrow":
        near = [sibling for atom in atoms for sibling in siblings(atom, shapes)]
        away = [permission for permission in (elsewhere(atom, other_names) for atom in atoms) if permission]
        return rng.sample(near, min(len(near), len(atoms))) + rng.sample(away, min(len(away), 1))
    scope = container if breadth == "medium" else top
    widened = []
    for atom in atoms:
        operations = [atom.operation] + [sibling.split(":")[1] for sibling in siblings(atom, shapes)]
        widened += [f"{atom.service}:{operation}:{scope(atom)}" for operation in operations]
    return widened + (BROAD_SANDBOX if breadth == "broad" else [])


def sender_holdings(key, breadth, shapes, other_names, seed):
    rng = random.Random(seed)
    return list(dict.fromkeys(key + RUNTIME + extras(key, breadth, shapes, other_names, rng)))
