"""F5 (RQ5, D-41): each fine-tuned helper, as the mean of its three seeds, against its untrained version, and the
smallest fine-tuned helper against prompted Qwen3-8B, on the synthetic held-out families. Excess authority in C, as in
F1 and F3; coverage is reported beside each test and is not tested."""

import argparse
import json
import re
from pathlib import Path

from mbla_bench import stats
from mbla_bench.analysis import COVERAGE, compare, per_task, with_holm

HELPERS = ["qwen3-reranker-0.6b", "qwen3-1.7b", "qwen3-4b", "qwen3-8b", "qwen3-reranker-8b"]
SMALLEST = "qwen3-reranker-0.6b"
REFERENCE = "qwen3-8b"


def seeds_merged(frame):
    frame = frame[~frame["method"].str.contains("untuned")].copy()
    frame["method"] = frame["method"].map(lambda method: re.sub(r"-s\d+$", "", method))
    keys = ["method", "item", "template", "handoff", "injected", "style"]
    return frame.groupby(keys, as_index=False).mean(numeric_only=True)


def with_coverage(frame, test):
    first, second = test["comparison"].split(" vs ")
    paired = stats.paired_difference(frame[frame["method"] == first], frame[frame["method"] == second], COVERAGE, cluster="template")
    return dict(test, coverage_difference=paired["difference"], coverage_low=paired["low"], coverage_high=paired["high"])


def f5(frame):
    pairs = [(f"{helper}-tuned", helper) for helper in HELPERS] + [(f"{SMALLEST}-tuned", REFERENCE)]
    tests = with_holm([compare(frame, first, second, "excess_C") for first, second in pairs])
    return [with_coverage(frame, test) for test in tests]


def write_markdown(path, tests):
    lines = ["# F5 (RQ5) fine-tuned vs untrained, synthetic held-out families", "", "Fine-tuned = mean of three seeds per task. Unit: family (8). Negative difference = less excess.", ""]
    lines += ["| Comparison | Families | Excess C difference | p | p (Holm) | Coverage difference [95%] |", "|---|---|---|---|---|---|"]
    lines += [f"| {t['comparison']} | {t['templates']} | {t['difference']:.3f} | {t['p']:.4f} | {t['p_holm']:.4f} | {t['coverage_difference']:.3f} [{t['coverage_low']:.3f}, {t['coverage_high']:.3f}] |" for t in tests]
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="F5 fine-tuning tests")
    parser.add_argument("--experiment", default="heldout")
    arguments = parser.parse_args()
    tests = f5(seeds_merged(per_task(arguments.experiment)))
    out = Path("results/tables") / arguments.experiment / "f5.md"
    write_markdown(out, tests)
    out.with_suffix(".json").write_text(json.dumps(tests, indent=2, default=float) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
