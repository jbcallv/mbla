import pytest

from mbla_bench.synth import audit, rekey


def rows():
    return [{"row": str(number), "permission": f"p{number}", "task": "t", "receiver": "r"} for number in (7, 8, 9)]


def test_compact_numbers_permissions_in_sheet_order():
    assert audit.compact_row("1", rows())["permissions"] == "1. p7\n2. p8\n3. p9"


def test_unmarked_permission_is_unneeded():
    entry = {"task_number": "1", "required": "1", "plausible": "3"}
    assert [row["answer"] for row in audit.expanded(rows(), entry)] == ["required", "unneeded", "plausible"]


@pytest.mark.parametrize("required, plausible", [("1", "1"), ("4", "")])
def test_bad_positions_are_refused(required, plausible):
    with pytest.raises(ValueError):
        audit.expanded(rows(), {"task_number": "1", "required": required, "plausible": plausible})


def task(text, plans, **fields):
    return {"request": {"text": text}, "attacks": [], "injected_attack": None, "plans": plans, **fields}


def test_conditional_step_gets_a_check():
    plan = ["github:issue.read:a/*", "github:issue.write:a/*"]
    assert rekey.settled(task("Read it. If so, close it.", [plan]))["check"] == plan[:1]


def test_check_without_a_condition_is_removed():
    plan = ["github:issue.read:a/*", "github:issue.comment:a/*"]
    assert "check" not in rekey.settled(task("Read it and comment.", [plan], check=plan[:1]))


def test_verify_if_is_not_a_condition():
    plan = ["github:issue.read:a/*", "github:issue.comment:a/*"]
    assert "check" not in rekey.settled(task("Verify if it is fixed and comment.", [plan]))


def test_second_plan_is_dropped_but_an_unused_folder_is_not_kept():
    put, read, folder = "storage:object.put:b/*", "storage:object.get:b/*", "fs:rw:/artifacts"
    assert rekey.settled(task("Upload it.", [[put], [read, put]]))["plans"] == [[put]]
    assert rekey.settled(task("Upload it.", [[folder, put], [put]]))["plans"] == [[put]]


def test_changelog_task_reads_the_issue_it_comments_on():
    plan = ["net:connect:pypi.org:443", "github:issue.comment:a/b/issues/1/*"]
    fixed = rekey.with_issue_read({"plans": [plan], "parent": plan})
    assert "github:issue.read:a/b/issues/1/*" in fixed["plans"][0] and "github:issue.read:a/b/issues/1/*" in fixed["parent"]


def test_folder_stays_only_when_the_task_names_it():
    plan = ["fs:rw:/artifacts", "github:actions.read:a/*"]
    assert rekey.without_unnamed_folder(task("Pull it.", [plan]))["plans"] == [plan[1:]]
    assert rekey.without_unnamed_folder(task("Pull it into the artifacts folder.", [plan]))["plans"] == [plan]
