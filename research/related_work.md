# Related Work: permission inference and minimization for agents

Collected 2026-10-02 for MBLA's benchmark design. Details come from arXiv abstract and HTML pages; check each against the PDF before citing.

## Closest: inferring least-privilege permissions for an agent task

| Work | What it infers | Models | Data | Minimality metric | Artifacts |
|---|---|---|---|---|---|
| **Progent** (Shi et al., arXiv 2504.11703) | per-query tool-call policy (symbolic rules over tool names and arguments), updated during execution; narrowing auto-applied, expansion needs approval | gpt-4o primary; ablation over several policy LLMs | AgentDojo (4 suites), ASB | none: utility and attack success rate only | not stated |
| **Conseca** (Tsai et al., Google, HotOS 2025, arXiv 2501.17070) | just-in-time contextual policy from the trusted request, deterministic enforcer | LLM policy generator | position paper | none | none |
| **MiniScope** (arXiv 2512.11147) | permission scopes for tool calls via reconstructed permission hierarchies; compared with an LLM baseline ("LLMScope") | LLM baseline: GPT-5, Claude Sonnet 4.5, Gemini 2.5 Flash, Llama 3.1-70B, Qwen3-30B | 1,558 synthetic requests over 10 real apps (Gmail, Drive, Slack, …) | over-privilege ratio = methods allowed by the LLM's scopes / by MiniScope's (1.04–2.19) | dataset "will be released"; no link |
| **FORTIS** (Li et al., arXiv 2605.09163) | over-privilege in agent skills: choosing the minimally sufficient skill, then its tools | 10 frontier models (GPT-5.5/5.4/5.4-mini, Claude Sonnet 4.6, Opus 4.7, Gemini 3.1-Pro, 3 Flash, Qwen 3.6-Max, Kimi K2.6, DeepSeek-V4-Flash) | 2,143 queries; email, e-commerce, filesystem; structural ground truth plus manual check of 200 (96.5% agreement) | exact match, over-privilege rate, no-action rate | **released**: github.com/lili0415/FORTIS-Benchmark |
| **Intent-Governed Tool Authorization** (arXiv 2606.22916) | intent certificate from the trusted request filters the tool manifest and validates actions; models are untrusted advisors | rule-based, hybrid rule+model; 3 models end to end | 176 synthetic instances; 34-task suite; 25-task transfer set from AgentDojo, ToolSandbox, tau-bench, ToolEmu | unsafe tool exposure, unsafe accepted authority, manifest reduction, over-defense | traces and microbenchmarks in appendices |
| **SkillScope** (Wu et al., arXiv 2605.05868) | over-privileged actions in agent skills via graph and static analysis plus runtime validation | not LLM inference | 68,312 real skills | skill-level F1 for detecting over-privilege (94.5%) | arXiv only |

## Classic precursor: text → permissions (per-permission classifiers)

- **WHYPER** (Pandita et al., USENIX Security 2013) and **AutoCog** (Qu et al., CCS 2014): decide from an Android app description whether each permission is justified, one classifier per permission. These are the historical ancestors of MBLA's decision-model paradigm (one yes/no per permission). AutoCog: 92.6% precision / 92.0% recall over 11 permissions.

## Delegation and attenuation (BoundClaw context, not MBLA inference)

- **Bounded Agents** (arXiv 2608.15888), **Delegation Without Trust** (arXiv 2609.00267): attenuation, multi-hop delegation, MCP/OAuth gaps.

## What nobody has done (MBLA's gap)

1. **Nobody benchmarks decision models** (rerankers, System One models like Jev/Laya/CLM) for permission inference. All prior LLM work generates policies with chat LLMs, mostly hosted frontier APIs.
2. **No direct minimality metric for generated policies**, except MiniScope's ratio and FORTIS's over-privilege rate. Progent and Conseca report only utility and attack success.
3. **No latency or cost comparison** of policy inference on the delegation path.
4. **No human-reviewed minimal references with reported agreement,** except FORTIS's spot check (200 queries).
5. **No recovery (step-up) admission analysis.** Progent's "expansion requires approval" is the closest; it uses a human, not a scored admit set.

## Reuse options

- **FORTIS data (released):** the only reusable public benchmark found. Possible external-validation set: map each skill or tool to a permission and run both paradigms. Domains differ from ours (email, e-commerce, filesystem).
- **MiniScope dataset:** not released yet; could ask the authors. Its 10-app request set is the closest match to MBLA's problem.
- **Metrics:** report FORTIS-style exact match and over-privilege rate alongside EAC/MAC for comparability (cheap: `exact_match` exists; over-privilege rate = share of items with any excess).
- **Models for comparability:** MiniScope's open models (Llama 3.1-70B, Qwen3-30B) and Progent's gpt-4o are the reference points prior work used.
