import argparse
import ast
import importlib.util
import json
import subprocess
from collections import Counter
from pathlib import Path

from mbla_bench import data, stats

REPOSITORY = "https://github.com/lili0415/FORTIS-Benchmark"
PINNED_COMMIT = "c67e8833bff19932c652f3a98b5d3bf7d959a980"
SOURCE = Path("data/external/fortis-src")
OUTPUT = Path("data/external/fortis")
DOMAINS = ["email", "ecommerce", "filesystem"]
FORTIS_CLASSES = ["exact_match", "under_privilege", "over_privilege", "no_action"]


def fetch():
    if not SOURCE.exists():
        subprocess.run(["git", "clone", "-q", REPOSITORY, str(SOURCE)], check=True)
    subprocess.run(["git", "-C", str(SOURCE), "checkout", "-q", PINNED_COMMIT], check=True)


def read_json(relative_path):
    return json.loads((SOURCE / relative_path).read_text())


def skill_permission(domain, skill_name):
    return f"{domain}:{skill_name}:skill"


def tool_permission(domain, tool_name):
    return f"{domain}:{tool_name}:tool"


def tool_descriptions(domain):
    tree = ast.parse((SOURCE / f"shared/scenarios/{domain}/tools.py").read_text())
    tools = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and any(getattr(decorator, "id", "").endswith("_tool") for decorator in node.decorator_list):
            tools[node.name] = (ast.get_docstring(node) or "").strip()
    return tools


def skill_document(domain, skill_name):
    return (SOURCE / f"shared/skills/{domain}/{skill_name}/SKILL.md").read_text()


def fortis_item(item_id, domain, text, candidates, reference, attacks, extra):
    return {
        "id": item_id,
        "template": f"{domain}-{extra['category']}",
        "split": "external",
        "request": {
            "protocol": "fortis",
            "operation": f"{extra['task']}.{domain}",
            "arguments": {},
            "text": text,
            "history": [],
            "manifest": [],
        },
        "parent": candidates,
        "ceiling": candidates,
        "reference": reference,
        "alternates": [],
        "attacks": attacks,
        "fortis": extra,
    }


def skill_selection_items(domain, dropped):
    skills = read_json(f"shared/scenarios/{domain}/skills.json")["skills"]
    listed = {skill["name"] for skill in skills}
    candidates = [skill_permission(domain, skill["name"]) for skill in skills]
    items = []
    for query in read_json(f"tasks/task1_skill_selection/scenarios/{domain}/queries.json")["queries"]:
        if query["gt_skill"] not in listed:
            dropped["unlisted_gt_skill"].append(query["id"])
            continue
        traps = [trap["skill"] for trap in query.get("trap_skills", [])]
        dropped["unlisted_trap_skill"] += [f"{query['id']}:{trap}" for trap in traps if trap not in listed]
        attacks = [{"id": f"trap-{trap}", "needs": [skill_permission(domain, trap)]} for trap in traps if trap in listed]
        extra = {
            "task": "task1",
            "category": query["category"],
            "gt_skill": query["gt_skill"],
            "gt_level": query["gt_level"],
            "skills": skills,
        }
        items.append(
            fortis_item(query["id"], domain, query["query"], candidates, [skill_permission(domain, query["gt_skill"])], attacks, extra)
        )
    return items


def tool_selection_text(domain, query):
    return f"{query['query']}\n\nAssigned skill: {query['given_skill']}\n\n{skill_document(domain, query['given_skill'])}"


def tool_selection_items(domain):
    candidates = [tool_permission(domain, tool) for tool in tool_descriptions(domain)]
    items = []
    for query in read_json(f"tasks/task2_tool_selection/scenarios/{domain}/queries.json")["queries"]:
        reference = [tool_permission(domain, tool) for tool in query["gt_tools"]]
        extra = {"task": "task2", "category": query["category"], "gt_tools": query["gt_tools"]}
        items.append(fortis_item(f"{domain}-{query['id']}", domain, tool_selection_text(domain, query), candidates, reference, [], extra))
    return items


def universe():
    operations = []
    for domain in DOMAINS:
        for skill in read_json(f"shared/scenarios/{domain}/skills.json")["skills"]:
            operations.append({"service": domain, "operation": skill["name"], "description": skill["description"]})
        for tool, description in tool_descriptions(domain).items():
            operations.append({"service": domain, "operation": tool, "description": description})
    return {"version": 1, "source": f"{REPOSITORY}@{PINNED_COMMIT}", "operations": operations}


def write_jsonl(path, items):
    path.write_text("".join(json.dumps(item) + "\n" for item in items))
    print(f"{path}: {len(items)} items")


def build():
    fetch()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    dropped = {"unlisted_gt_skill": [], "unlisted_trap_skill": []}
    write_jsonl(OUTPUT / "task1.jsonl", [item for domain in DOMAINS for item in skill_selection_items(domain, dropped)])
    (OUTPUT / "dropped.json").write_text(json.dumps(dropped, indent=2) + "\n")
    print(
        f"dropped {len(dropped['unlisted_gt_skill'])} task1 queries with an unlisted gt skill; {len(dropped['unlisted_trap_skill'])} unlisted trap skills"
    )
    write_jsonl(OUTPUT / "task2.jsonl", [item for domain in DOMAINS for item in tool_selection_items(domain)])
    (OUTPUT / "universe.json").write_text(json.dumps(universe(), indent=2) + "\n")


def official_metrics(task):
    path = SOURCE / f"tasks/task{task[-1]}_{'skill' if task == 'task1' else 'tool'}_selection/eval/metrics.py"
    spec = importlib.util.spec_from_file_location(f"fortis_{task}_metrics", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def name_of(permission):
    return permission.split(":")[1]


def chosen_skill(row, item):
    best = max(row["scores"], default=0.0)
    if best <= 0:
        return ""
    levels = {skill["name"]: skill["level"] for skill in item["fortis"]["skills"]}
    tied = [name_of(candidate) for candidate, score in zip(row["candidates"], row["scores"]) if score == best]
    return max(tied, key=lambda skill: levels.get(skill, -1))


def classify(row, item, task1_metrics, task2_metrics):
    extra = item["fortis"]
    if extra["task"] == "task1":
        return task1_metrics.classify_skill_result(extra["gt_skill"], chosen_skill(row, item), extra["gt_level"], extra["skills"])
    return task2_metrics.classify_result(extra["gt_tools"], [name_of(permission) for permission in row["initial"]])


def summarize(rows, items):
    task1_metrics, task2_metrics = official_metrics("task1"), official_metrics("task2")
    counts = {}
    for row in rows:
        counts.setdefault(row["method"], Counter())[classify(row, items[row["item"]], task1_metrics, task2_metrics)] += 1
    summary = []
    for method, method_counts in sorted(counts.items()):
        total = sum(method_counts.values())
        rates = {name: method_counts[name] / total for name in FORTIS_CLASSES}
        summary.append(
            {
                "method": method,
                "items": total,
                **rates,
                "safe_rate": rates["exact_match"] + rates["under_privilege"],
                "fail_rate": rates["over_privilege"] + rates["no_action"],
            }
        )
    return summary


def report(experiment, items_path):
    items = data.items_by_id(items_path)
    rows = data.load_predictions(Path("results/raw") / experiment)
    summary = summarize(rows, items)
    table = Path("results/tables") / f"{experiment}_fortis_metrics.json"
    table.write_text(json.dumps(summary, indent=2) + "\n")
    for entry in summary:
        print(
            f"{entry['method']:24} n={entry['items']:5} EM={entry['exact_match']:.3f} OPR={entry['over_privilege']:.3f} NAR={entry['no_action']:.3f} safe={entry['safe_rate']:.3f}"
        )


def exact_by_item(rows, items, method, task1_metrics, task2_metrics):
    return {
        row["item"]: classify(row, items[row["item"]], task1_metrics, task2_metrics) == "exact_match"
        for row in rows
        if row["method"] == method
    }


def compare_methods(experiment, items_path, first, second):
    items = data.items_by_id(items_path)
    rows = data.load_predictions(Path("results/raw") / experiment)
    task1_metrics, task2_metrics = official_metrics("task1"), official_metrics("task2")
    first_exact = exact_by_item(rows, items, first, task1_metrics, task2_metrics)
    second_exact = exact_by_item(rows, items, second, task1_metrics, task2_metrics)
    shared = sorted(set(first_exact) & set(second_exact))
    result = {
        "experiment": experiment,
        "first": first,
        "second": second,
        "items": len(shared),
        "first_exact": sum(first_exact[item] for item in shared) / len(shared),
        "second_exact": sum(second_exact[item] for item in shared) / len(shared),
        "mcnemar_p": stats.mcnemar_exact([first_exact[item] for item in shared], [second_exact[item] for item in shared]),
    }
    print(json.dumps(result))
    return result


def main():
    parser = argparse.ArgumentParser(
        description="FORTIS external validation: build items from the pinned FORTIS release, score with its official metrics"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build")
    report_command = commands.add_parser("report")
    report_command.add_argument("experiment")
    report_command.add_argument("items")
    compare_command = commands.add_parser("compare")
    compare_command.add_argument("experiment")
    compare_command.add_argument("items")
    compare_command.add_argument("first")
    compare_command.add_argument("second")
    arguments = parser.parse_args()
    if arguments.command == "build":
        build()
    elif arguments.command == "compare":
        compare_methods(arguments.experiment, arguments.items, arguments.first, arguments.second)
    else:
        report(arguments.experiment, arguments.items)


if __name__ == "__main__":
    main()
