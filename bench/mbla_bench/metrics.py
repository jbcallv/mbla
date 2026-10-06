from mbla_bench import reference

KINDS = ["C", "N", "F", "X"]


def policy(texts):
    return reference.parse_all(texts)


def item_universe(item, row):
    needs = [need for attack in item["attacks"] for need in attack["needs"]]
    return reference.action_universe(policy(row["candidates"]), policy(item["reference"]), policy(needs), policy(item["parent"]))


def of_kind(actions, kind):
    return {action for action in actions if action.kind == kind}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def component_metrics(held, required, granted, kind):
    held, required, granted = of_kind(held, kind), of_kind(required, kind), of_kind(granted, kind)
    return {
        f"eac_{kind}": ratio(len(granted - required), len(held - required)),
        f"mac_{kind}": ratio(len(required - granted), len(required)),
        f"empty_ok_{kind}": None if required else not granted,
    }


def item_metrics(item, row, granted_texts=None):
    universe = item_universe(item, row)
    held = reference.denotation(policy(item["parent"]), universe)
    required = reference.denotation(policy(item["reference"]), universe)
    granted_policy = policy(row["initial"] if granted_texts is None else granted_texts)
    granted = reference.denotation(granted_policy, universe)
    metrics = {
        "exact_match": granted == required,
        "precision": ratio(len(granted & required), len(granted)),
        "recall": ratio(len(granted & required), len(required)),
        "eac": ratio(len(granted - required), len(held - required)),
        "mac": ratio(len(required - granted), len(required)),
        "size": len(granted_policy),
        "over_privileged": bool(granted - required),
        "no_action": not granted_policy,
    }
    for kind in KINDS:
        metrics.update(component_metrics(held, required, granted, kind))
    return metrics


def f1(metrics):
    precision, recall = metrics["precision"] or 0.0, metrics["recall"] or 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def calibration_pairs(item, row):
    required = policy(item["reference"])
    labels = [reference.within([candidate], required) for candidate in policy(row["candidates"])]
    return list(zip(row["scores"], labels))


def expected_calibration_error(pairs, bins=10):
    if not pairs:
        return None
    total_error = 0.0
    for bin_index in range(bins):
        low, high = bin_index / bins, (bin_index + 1) / bins
        members = [(score, label) for score, label in pairs if low <= score < high or (bin_index == bins - 1 and score == 1.0)]
        if members:
            mean_score = sum(score for score, _ in members) / len(members)
            accuracy = sum(label for _, label in members) / len(members)
            total_error += len(members) / len(pairs) * abs(mean_score - accuracy)
    return total_error
