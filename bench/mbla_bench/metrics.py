"""per-task metrics against the least-authority plan (final methodology §8)."""

from mbla_bench import answer, reference

COMPONENTS = ["C", "plain", "D"]


def policy(texts):
    return reference.parse_all(texts)


def of_kind(actions, kind):
    return {action for action in actions if action.kind == kind}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def components(item):
    return ["C", "plain"] if item["request"]["receiver"]["remote"] else COMPONENTS


def component_metrics(held, required, granted, kind):
    held, required, granted = of_kind(held, kind), of_kind(required, kind), of_kind(granted, kind)
    return {
        f"excess_{kind}": ratio(len(granted - required), len(held - required)),
        f"missing_{kind}": ratio(len(required - granted), len(required)),
        f"exact_{kind}": granted == required,
        f"empty_ok_{kind}": None if required else not granted,
    }


def item_metrics(item, row, granted_texts=None, required=None):
    required = answer.tiers(item)[0] if required is None else required
    granted_policy = policy(row["initial"] if granted_texts is None else granted_texts)
    actions = answer.universe(item, extra=(granted_policy,))
    held = reference.denotation(policy(item["parent"]), actions)
    needed = reference.denotation(required, actions)
    granted = reference.denotation(granted_policy, actions)
    metrics = {
        "precision": ratio(len(granted & needed), len(granted)),
        "recall": ratio(len(granted & needed), len(needed)),
        "size": len(granted_policy),
        "decoy": any(atom.kind == "plain" for atom in granted_policy),
    }
    for kind in components(item):
        metrics.update(component_metrics(held, needed, granted, kind))
    return metrics


def f1(metrics):
    precision, recall = metrics["precision"] or 0.0, metrics["recall"] or 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0
