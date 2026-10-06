import argparse
import csv
import json
import subprocess
import tempfile
from pathlib import Path

from mbla_bench import data, reference, stats

COLUMNS = ["template", "split", "task", "arguments", "permission", "meaning", "needed", "note"]
KIND_ORDER = {"C": 0, "N": 1, "F": 2, "X": 3}


def example_items(task_paths):
    items = [item for path in task_paths for item in data.read_jsonl(path)]
    return [item for item in items if item["breadth"] == "broad" and item["id"].endswith("-b0-benign")]


def candidates_by_item(items, mbla_binary):
    with tempfile.TemporaryDirectory() as scratch:
        items_path, output_path = Path(scratch) / "items.jsonl", Path(scratch) / "out.jsonl"
        items_path.write_text("".join(json.dumps(item) + "\n" for item in items))
        subprocess.run([mbla_binary, "bench", "-items", items_path, "-out", output_path, "-warmup", "0"], check=True)
        return {row["item"]: row["candidates"] for row in data.read_jsonl(output_path)}


def glossary(universe_path):
    universe = json.loads(Path(universe_path).read_text())
    return {f"{entry['service']}:{entry['operation']}": entry["description"] for entry in universe["operations"]}


def sheet_rows(item, candidates, meanings):
    ordered = sorted(candidates, key=lambda text: (KIND_ORDER[reference.parse(text).kind], text))
    for permission in ordered:
        atom = reference.parse(permission)
        yield {
            "template": item["template"],
            "split": item["split"],
            "task": item["request"]["text"],
            "arguments": json.dumps(item["request"]["arguments"]),
            "permission": permission,
            "meaning": meanings.get(f"{atom.service}:{atom.operation}", ""),
            "needed": "",
            "note": "",
        }


def write_sheet(path, rows):
    with open(path, "w", newline="") as sheet:
        writer = csv.DictWriter(sheet, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def make_sheets(arguments):
    items = example_items(arguments.tasks)
    candidates = candidates_by_item(items, arguments.mbla)
    meanings = glossary(arguments.universe)
    rows = [row for item in items for row in sheet_rows(item, candidates[item["id"]], meanings)]
    for reviewer in arguments.reviewers.split(","):
        path = Path(arguments.out_dir) / f"audit_{reviewer}.csv"
        write_sheet(path, rows)
        print(f"{path}: {len(rows)} rows across {len(items)} templates")


LABELS = {"1": "1", "yes": "1", "y": "1", "0": "0", "no": "0", "n": "0"}


def normalized(label):
    return LABELS.get(label.strip().lower(), "unclear")


def read_sheet(path):
    with open(path, newline="", encoding="utf-8-sig") as sheet:
        rows = list(csv.DictReader(sheet))
    return {(row["template"], row["permission"]): row for row in rows}


def reviewer_name(path):
    return Path(path).stem.removeprefix("audit_")


def draft_labels(task_paths):
    references = {item["template"]: reference.parse_all(item["reference"]) for item in example_items(task_paths)}
    return lambda template, permission: "1" if reference.within([reference.parse(permission)], references[template]) else "0"


def labels_by_rater(sheets, keys, draft):
    labels = {name: [normalized(sheet[key]["needed"]) for key in keys] for name, sheet in sheets.items()}
    labels["draft"] = [draft(*key) for key in keys]
    return labels


def decided_pairs(first_labels, second_labels):
    return [(a, b) for a, b in zip(first_labels, second_labels) if "unclear" not in (a, b)]


def kappa_of(pairs):
    return stats.cohen_kappa([a for a, _ in pairs], [b for _, b in pairs]) if pairs else None


def pairs_by_template(labels, keys, first, second):
    groups = {}
    for index, key in enumerate(keys):
        pair = (labels[first][index], labels[second][index])
        if "unclear" not in pair:
            groups.setdefault(key[0], []).append(pair)
    return list(groups.values())


def pair_statistics(labels, keys, first, second):
    pairs = decided_pairs(labels[first], labels[second])
    low, high = stats.cluster_bootstrap_interval(pairs_by_template(labels, keys, first, second), kappa_of)
    return {
        "decided_rows": len(pairs),
        "percent_agreement": sum(a == b for a, b in pairs) / len(pairs),
        "cohen_kappa": kappa_of(pairs),
        "kappa_95ci_template_bootstrap": [low, high],
        "both_needed": sum(a == b == "1" for a, b in pairs),
        "both_not_needed": sum(a == b == "0" for a, b in pairs),
        f"only_{first}_needed": sum(a == "1" and b == "0" for a, b in pairs),
        f"only_{second}_needed": sum(a == "0" and b == "1" for a, b in pairs),
    }


def rater_pairs(names):
    return [(first, second) for index, first in enumerate(names) for second in names[index + 1 :]]


def alpha_over(labels, names):
    units = [[labels[name][index] for name in names if labels[name][index] != "unclear"] for index in range(len(labels[names[0]]))]
    return stats.krippendorff_alpha_nominal(units)


def breakdown(labels, keys, group_of):
    groups = sorted({group_of(key) for key in keys})
    humans = [name for name in labels if name != "draft"]
    rows = []
    for group in groups:
        indexes = [index for index, key in enumerate(keys) if group_of(key) == group]
        row = {"group": group, "rows": len(indexes)}
        for first, second in rater_pairs(list(labels)):
            pairs = decided_pairs([labels[first][i] for i in indexes], [labels[second][i] for i in indexes])
            row[f"agree_{first}_{second}"] = sum(a == b for a, b in pairs) / len(pairs) if pairs else None
        for name in humans:
            row[f"unclear_{name}"] = sum(labels[name][i] == "unclear" for i in indexes)
        rows.append(row)
    return rows


def audit_summary(labels, keys, disagreements):
    names = list(labels)
    humans = [name for name in names if name != "draft"]
    return {
        "rows": len(keys),
        "templates": len({key[0] for key in keys}),
        "raters": names,
        "note": "draft = references drafted by Claude from the templates; human-vs-human agreement is the reliability measure",
        "unclear": {name: labels[name].count("unclear") for name in humans},
        "needed_counts": {name: labels[name].count("1") for name in names},
        "pairs": {f"{first}_vs_{second}": pair_statistics(labels, keys, first, second) for first, second in rater_pairs(names)},
        "krippendorff_alpha_humans": alpha_over(labels, humans) if len(humans) > 1 else None,
        "krippendorff_alpha_all": alpha_over(labels, names),
        "rows_to_resolve": len(disagreements),
    }


def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="") as sheet:
        writer = csv.DictWriter(sheet, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def disagreement_rows(sheets, keys, labels):
    rows = []
    for index, key in enumerate(keys):
        row_labels = {name: values[index] for name, values in labels.items()}
        if len(set(row_labels.values())) > 1:
            notes = {f"{name}_note": sheet[key]["note"] for name, sheet in sheets.items()}
            rows.append({"template": key[0], "permission": key[1], **row_labels, **notes, "resolved": ""})
    return rows


def previous_resolutions(path):
    if not path.exists() or not path.read_text().strip():
        return {}
    with open(path, newline="") as sheet:
        return {(row["template"], row["permission"]): row["resolved"] for row in csv.DictReader(sheet)}


def keep_resolutions(disagreements, path):
    resolved = previous_resolutions(path)
    return [dict(row, resolved=resolved.get((row["template"], row["permission"]), "")) for row in disagreements]


def all_label_rows(sheets, keys, labels):
    return [
        {"template": key[0], "permission": key[1], **{name: values[index] for name, values in labels.items()}}
        for index, key in enumerate(keys)
    ]


def compare(arguments):
    sheets = {reviewer_name(path): read_sheet(path) for path in arguments.sheets}
    keys = sorted(set.intersection(*(set(sheet) for sheet in sheets.values())))
    labels = labels_by_rater(sheets, keys, draft_labels(arguments.tasks))
    disagreements = keep_resolutions(disagreement_rows(sheets, keys, labels), Path(arguments.out))
    summary = audit_summary(labels, keys, disagreements)
    tables = Path(arguments.tables)
    write_csv(Path(arguments.out), disagreements)
    write_csv(Path("data/review/audit_labels.csv"), all_label_rows(sheets, keys, labels))
    write_csv(tables / "reference_audit_by_template.csv", breakdown(labels, keys, lambda key: key[0]))
    write_csv(tables / "reference_audit_by_kind.csv", breakdown(labels, keys, lambda key: reference.parse(key[1]).kind))
    (tables / "reference_audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"{arguments.out}: {len(disagreements)} rows to resolve")


def human_names(label_row):
    return [name for name in label_row if name not in ("template", "permission", "draft")]


def final_label(label_row, resolution):
    if resolution:
        return normalized(resolution), "resolved"
    human_labels = {label_row[name] for name in human_names(label_row)}
    if len(human_labels) == 1 and "unclear" not in human_labels:
        return human_labels.pop(), "unanimous"
    return None, "unresolved"


def final_rows(labels_path, disagreements_path):
    resolutions = previous_resolutions(disagreements_path)
    with open(labels_path, newline="") as sheet:
        label_rows = list(csv.DictReader(sheet))
    rows = []
    for label_row in label_rows:
        key = (label_row["template"], label_row["permission"])
        label, source = final_label(label_row, resolutions.get(key, ""))
        rows.append({"template": key[0], "permission": key[1], "final": label, "source": source})
    return rows


def finalize(arguments):
    rows = final_rows(Path(arguments.labels), Path(arguments.disagreements))
    unresolved = [row for row in rows if row["final"] is None]
    if unresolved:
        raise SystemExit(
            f"{len(unresolved)} rows still need a resolution, e.g. {[(r['template'], r['permission']) for r in unresolved[:3]]}"
        )
    write_csv(Path(arguments.out), rows)
    draft = draft_labels(arguments.tasks)
    mismatches = [row for row in rows if draft(row["template"], row["permission"]) != row["final"]]
    for row in mismatches:
        print(f"reference differs from final label: {row['template']} {row['permission']} final={row['final']} ({row['source']})")
    print(f"{arguments.out}: {len(rows)} final labels; {len(mismatches)} differ from the current references")
    if mismatches:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description="reference audit: blank sheets per reviewer, then compare")
    parser.add_argument("--tasks", nargs="+", default=["data/tasks/dev.jsonl", "data/tasks/test.jsonl"])
    commands = parser.add_subparsers(dest="command", required=True)
    sheets_command = commands.add_parser("sheets")
    sheets_command.add_argument("--reviewers", required=True, help="comma-separated names, one sheet each")
    sheets_command.add_argument("--mbla", default="../mbla/bin/mbla")
    sheets_command.add_argument("--universe", default="data/universe.json")
    sheets_command.add_argument("--out-dir", default="data/review")
    compare_command = commands.add_parser("compare")
    compare_command.add_argument("sheets", nargs="+", help="one or more filled audit_<name>.csv files")
    compare_command.add_argument("--out", default="data/review/audit_disagreements.csv")
    compare_command.add_argument("--tables", default="results/tables")
    final_command = commands.add_parser("final")
    final_command.add_argument("--labels", default="data/review/audit_labels.csv")
    final_command.add_argument("--disagreements", default="data/review/audit_disagreements.csv")
    final_command.add_argument("--out", default="data/review/audit_final.csv")
    arguments = parser.parse_args()
    commands_by_name = {"sheets": make_sheets, "compare": compare, "final": finalize}
    commands_by_name[arguments.command](arguments)


if __name__ == "__main__":
    main()
