from mbla_bench import reference

MODES = ["bound-only", "admitted"]


def policy(texts):
    return reference.parse_all(texts)


def select(candidates, scores, threshold):
    return [candidate for candidate, score in zip(candidates, scores) if score >= threshold]


def with_thresholds(row, initial, admit):
    return dict(row, initial=select(row["candidates"], row["scores"], initial), admit=select(row["candidates"], row["scores"], admit))


def thresholds_consistent(row):
    initial, admit = row["thresholds"]
    recomputed = with_thresholds(row, initial, admit)
    return recomputed["initial"] == row["initial"] and recomputed["admit"] == row["admit"]


def admits(mode, row, item, atom):
    if not atom.is_concrete or not reference.covered(policy(item["ceiling"]), atom):
        return False
    admission_set = item["parent"] if mode == "bound-only" else row["admit"]
    return reference.covered(policy(admission_set), atom)


def uncovered(granted, needs):
    return [need for need in policy(needs) if not reference.covered(granted, need)]


def reachable_with_recovery(mode, row, item, needs, cap):
    missing = uncovered(policy(row["initial"]), needs)
    return len(missing) <= cap and all(admits(mode, row, item, atom) for atom in missing)


def simulate(item, row, mode, cap):
    missing = uncovered(policy(row["initial"]), item["reference"])
    attacks = item["attacks"]
    reached_initial = [attack for attack in attacks if not uncovered(policy(row["initial"]), attack["needs"])]
    reached_recovery = [attack for attack in attacks if reachable_with_recovery(mode, row, item, attack["needs"], cap)]
    return {
        "mode": mode,
        "cap": cap,
        "recoveries": len(missing),
        "recoveries_capability": sum(1 for atom in missing if atom.kind == "C"),
        "recoveries_sandbox": sum(1 for atom in missing if atom.kind != "C"),
        "success": reachable_with_recovery(mode, row, item, item["reference"], cap),
        "ras_initial": len(reached_initial) / len(attacks) if attacks else None,
        "ras_recovery": len(reached_recovery) / len(attacks) if attacks else None,
    }
