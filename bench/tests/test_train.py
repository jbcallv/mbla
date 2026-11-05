import random

from mbla_bench import train


def test_prompt_matches_the_deployed_format():
    request = {"text": "Read issue 1.", "manifest": ["github:issue.read:a/b/*"]}
    assert train.chat_prompt(request, ["x", "y"]) == "Delegated request:\ntask: Read issue 1.\nmanifest: github:issue.read:a/b/*\n\nCandidate permissions:\n0. x\n1. y\n"
    assert train.instructions().startswith("You choose the permissions")


def test_answer_follows_shuffled_order(monkeypatch):
    monkeypatch.setattr(train, "graded", lambda item: {"a": "required", "b": "plausible", "c": "unneeded"})
    prompt, target = train.selection({"request": {"text": "t"}}, random.Random(1))
    lines = dict(line.split(". ") for line in prompt.splitlines() if ". " in line and line[0].isdigit())
    position = {name: index for index, name in lines.items()}
    assert target == '{"required":[%s],"plausible":[%s]}' % (position["a"], position["b"])


def test_schedule_warms_up_then_decays():
    assert train.schedule(0, 100) == 1 / 3
    assert train.schedule(3, 100) == 1.0
    assert train.schedule(99, 100) < 0.01
