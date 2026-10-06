# MBLA: task-scoped permission inference for BoundClaw

MBLA is the policy-inference and recovery-admission component of BoundClaw. At every delegation it proposes the capability and confinement permissions a receiver needs, choosing only from what the delegator already holds. When a receiver is denied mid-task, it decides whether a single recovery request is granted. The trusted checks bound every proposal, so an inference mistake costs utility, never safety.

## Repository map

| Directory | What it is | Who needs it |
|---|---|---|
| [`mbla/`](mbla/) | **Core Go package** (standard library only): permissions, attenuation and ceiling checks, recovery admission, policy proposal, scorer clients | the gVisor fork imports this |
| [`bench/`](bench/) | Replication package: dataset, model serving, experiment runner, metrics, statistics | anyone reproducing results |
| [`plots/`](plots/) | gnuplot scripts and their data files (exported from `bench/results/tables`) | paper figures |
| [`report/`](report/) | Short LaTeX overview of the findings, built by CI on every push | readers |
| [`research/`](research/) | Spec, decisions, assumptions, findings log, related work, paper alignment | the team |

## Using the core package

```
go get github.com/jbcallv/mbla/mbla
```

If the repository is private, set `GOPRIVATE=github.com/jbcallv/*` (or use a `replace` directive). The full delegation flow, with and without a model, is in [`mbla/README.md`](mbla/README.md):

1. Delegator: `Propose` (picks from the delegator's holdings), then `CheckAttenuation`.
2. Receiver: `ApplyCeiling`, install `Network()`, `Filesystem()`, `Executables()`.
3. Recovery: the receiver checks its ceiling and asks; the delegator calls `Recovery.Decide`.

Scorers: `SetOnly`, `ManifestOnly` and `Lexical` need no model. `ChatModel` (any OpenAI-compatible server), `DecisionModel` (a `/score` server such as Qwen3-Reranker) and `SystemOne` (Jev or CLM) call a model over HTTP.

## Headline results

On the paper's workflows (288 test items, references labeled by two humans, κ = 0.85):

- **Recovery.** Under the paper's recovery rule, a malicious receiver reaches 100% of the attacks its parent allows. Admitting only permissions the scorer rated plausible cuts this to 13% for Qwen3-8B, with 97% of legitimate tasks still succeeding.
- **Accuracy vs. latency.** Mid-size generative models (Qwen3 4B–32B) are the most precise, with excess capability authority below 0.1. Decision models answer in tens of milliseconds but over-grant zero-shot.
- **FORTIS.** Qwen3-Reranker-8B matches 30B–120B generators on skill selection.

Details and figures: [`report/`](report/) (the PDF is a CI artifact), [`research/findings.md`](research/findings.md).

## Reproducing

```
cd bench
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
make mbla data verify conform     # build, regenerate items, check freeze, checker conformance
bash serve/download.sh            # pinned model revisions
make dev tune e1 e3 e4 fortis     # see bench/README.md for the full order
make report && .venv/bin/python -m mbla_bench.export && make -C ../plots && make -C ../report
```

Raw predictions (about 135 MB) are not in git. They ship as the release asset `results-raw-v2.tar.gz`; extract it into `bench/results/raw/`.

## Alignment with the paper

[`research/paper_alignment.md`](research/paper_alignment.md) maps each paper section to its implementation and lists the deliberate differences:
- clipping to the ceiling instead of rejecting;
- the proposed `Admitted` recovery mode;
- FORTIS in place of AgentDojo.

## Scope

MBLA covers policy inference and recovery admission only. The enforcement layer (tunnel, sandbox construction, deny events, attestation) and the paper text are maintained separately.
