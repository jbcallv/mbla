import pytest

from mbla_bench.synth import audit


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
