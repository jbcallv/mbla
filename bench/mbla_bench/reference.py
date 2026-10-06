from dataclasses import dataclass

WITNESS = "~witness"


@dataclass(frozen=True)
class Atom:
    service: str
    operation: str
    resource: str
    qualifier: str = ""

    def __str__(self):
        text = f"{self.service}:{self.operation}:{self.resource}"
        return f"{text}?{self.qualifier}" if self.qualifier else text

    @property
    def kind(self):
        return {"net": "N", "fs": "F", "exec": "X"}.get(self.service, "C")

    @property
    def is_concrete(self):
        return "*" not in self.operation and "*" not in self.resource


def parse(text):
    parts = text.split(":", 2)
    if len(parts) != 3 or not all(parts):
        raise ValueError(f"permission {text!r}: want service:operation:resource")
    resource, _, qualifier = parts[2].partition("?")
    if "*" in resource[:-1]:
        raise ValueError(f"permission {text!r}: wildcard only allowed at the end")
    return Atom(parts[0], parts[1], resource, qualifier)


def parse_all(texts):
    return [parse(text) for text in texts]


def grants(pattern, concrete):
    return (
        pattern.service == concrete.service
        and pattern.operation in ("*", concrete.operation)
        and resource_grants(pattern.resource, concrete.resource)
        and pattern.qualifier in ("", concrete.qualifier)
    )


def resource_grants(pattern, resource):
    if pattern.endswith("*"):
        return resource.startswith(pattern[:-1])
    return resource == pattern or resource.startswith((pattern + "/", pattern + "#"))


def witnesses(atom):
    resource = atom.resource[:-1] + WITNESS if atom.resource.endswith("*") else atom.resource
    resources = {resource, resource + "/" + WITNESS, resource + "#" + WITNESS}
    operations = {atom.operation.replace("*", WITNESS)}
    qualifiers = {atom.qualifier} if atom.qualifier else {"", WITNESS}
    return {
        Atom(atom.service, operation, witness_resource, qualifier)
        for operation in operations
        for witness_resource in resources
        for qualifier in qualifiers
    }


def action_universe(*policies):
    universe = set()
    for policy in policies:
        for atom in policy:
            universe |= witnesses(atom)
    return universe


def denotation(policy, universe):
    return {action for action in universe if any(grants(pattern, action) for pattern in policy)}


def within(child, parent):
    universe = action_universe(child, parent)
    return denotation(child, universe) <= denotation(parent, universe)


def covered(policy, atom):
    return within([atom], policy)
