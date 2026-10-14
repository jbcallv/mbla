# Fine-tuning dataset and E1b (fine-tuned scorers)

Status: **proposed** (2026-10-13). Becomes pre-registered (D-21) once Joseph approves it, and before any generated item is used for training.

## Why

- Untrained yes/no scorers are fast but over-grant (F-24, F-26). CAPMAS was trained on its own data (ASTRA); we have compared it only against untrained scorers.
- No public dataset matches our task: sender holdings as the candidate pool, narrowed copies, receiver ceilings, planted attacks (survey in `related_work.md`, "Synthetic datasets and fine-tuning").
- Question for E1b: **does task-specific training let a small, fast model match Qwen3-8B's tightness at reranker latency?**

## Scope (aligned with the paper)

- Services: only those in the paper's workflows (§6.1):
  - BC-1: GitHub issue triage
  - BC-2: build, then upload to S3
  - BC-3: Google Docs fetch, then Slack post
  - plus `net`, `fs` and `exec` permissions
- Permission vocabulary within those services comes from the providers' published permission lists:
  - GitHub fine-grained token permissions and REST endpoints
  - Amazon S3 actions in the AWS Service Authorization Reference
  - Google Docs/Drive OAuth scopes
  - Slack OAuth scopes
- Same `service:operation:resource[?qualifier]` format and `Covers` rule as the benchmark.

## Generation (each step names the work it follows)

1. **Task families.**
   - About 40 families of delegated work across the three workflows (e.g. "label issues matching X", "upload a release artifact under prefix P", "post a doc summary to channel C").
   - About 8 families are held out of training entirely and used only for testing.
   - Follows: task families with an excluded-family validation split [T1].
2. **Task writing (pass 1).**
   - A local open model writes concrete tasks inside each family, seeded with our 17 benchmark templates as in-context examples [S1].
   - For each task it also writes the API call plan that performs it, as in tool-use data generation [S2, S3].
   - Generator: gpt-oss-120b. Run locally, so the data can be released.
3. **Labels from execution, not from a model (pass 2, separate).**
   - The call plan runs against mock services that log every access.
   - The answer key is the smallest set of permissions that covers every logged access, computed by `mbla.Policy.Covers`.
   - Follows:
     - AuthBench, gold permissions recorded with strace while running the reference solution [B1];
     - AWS IAM Access Analyzer, which generates least-privilege policies from access logs [P1];
     - Noyan, which separates generation and labeling into different passes to avoid circularity [B2].
4. **Automated checks (three stages)** [S3]:
   - **Format:** the plan parses and every call exists in the vocabulary.
   - **Execution:** the plan runs on the mocks without error.
   - **Semantic:** two different judge models (Qwen3-32B and Llama-3.3-70B, neither of them the generator) must both agree the plan accomplishes the task. Either one disagreeing drops the task [B3].
   - Description-neutrality and near-duplicate filters (MinHash over task text) as in [B3].
5. **Sender holdings and distractors.**
   - Each sender holds the answer key, plus the runtime permissions, plus extras at narrow, medium or broad breadth (as in the benchmark generator, D-13).
   - Hard negatives:
     - same resource, different action;
     - same action, wider scope;
     - a sibling service.
   - Hard negatives are standard for contrastive and reranker training [M3].
6. **Attack variants.**
   - Injected instructions are planted in the task text, and the answer key stays unchanged.
   - Follows AgentDojo-style prompt injection [B4] and our benchmark's attack design.
7. **Leakage control.**
   - No overlap with our frozen test set (`data/tasks/SHA256SUMS`): no shared names, resources, or 8-gram task text.
   - Checked automatically [D2].

Size: **2,000 tasks after filtering, split 1,500 train / 300 validation (training families) / 200 held-out families.**
- This is the split of T1 [T1], the closest precedent: least-privilege fine-tuning of a 4B model, at the same task granularity.
- It also matches ToolPrivBench's 1,994 SFT trajectories [B3], and sits between Noyan's 600 [B2] and ASTRA's ~3.2k (3 × 1,056) [C2].
- LIMA found about 1,000 varied, high-quality examples enough for narrow fine-tuning [D3].
- With 40 families that is 50 tasks per family (37–38 train).
- We generate until each family has 50 tasks that pass every check, and report the filter rate at each stage.
- A reranker sees about 10–15 yes/no pairs per task, about 18k training pairs.

| Work | Tasks | Used for training? |
|---|---|---|
| T1 (2608.18351) | 2,000 (1,500 / 300 / 200) | yes, Qwen3.5-4B |
| ToolPrivBench (2606.20023) | 544 benchmark + 1,994 SFT | yes, Qwen3-4B/8B |
| ASTRA (2510.26702) | about 3 × 1,056 | yes (by CAPMAS) |
| Noyan (2607.22445) | 600 | yes, RoBERTa-large |
| AuthBench (2605.14859) | 120 | no |
| **Ours** | **2,000 (1,500 / 300 / 200)** | yes |

## Vetting by humans (acceptance sampling)

What prior work did:
- AuthBench: humans cleaned every strace-derived label (120 tasks) [B1].
- ToolPrivBench: two annotators per scenario plus a third to break ties; agreement not reported [B3].
- Noyan: one reviewer, a 10% random sample (60 of 600), κ 0.917 → 0.967 over 688 decisions; no pass threshold [B2].
- T1: "reviewed" envelopes under human supervision; no numbers [T1].
- APIGen: automated checks only [S3].

Our protocol, which is stricter on every point except sample share:
- **Claim tested:** the generated answer keys' task-level error rate is below 5%, at 95% confidence (one-sided).
- **Sample:** **n = 93 tasks**, random and stratified by workflow and family, drawn after generation is frozen.
- **Pass rule:** **at most 1 task whose generated key differs from the adjudicated human key.**
  - This is the binomial zero/one-acceptance plan: the smallest n with P(X ≤ c | p = 0.05) ≤ 0.05.
  - Computed values: c = 0 → 59, c = 1 → 93, c = 2 → 124 [D4].
- **Fail rule:** fix the generator, regenerate, and audit a **fresh** sample. Never re-audit the same sample.
- **Labeling:**
  - Joseph and Alvi each label all 93 tasks **blind** to the generated key and to each other, which avoids anchoring.
  - They then adjudicate their disagreements together.
  - About 3–4 hours each.
- **Reported numbers:**
  - Human–human Cohen's κ over every permission decision (about 900 decisions), with a 95% CI [D5, D6].
  - Human–generator κ.
  - The task-level error count, with an exact Clopper–Pearson 95% CI [D7].
- **Why 93 and not 350:**
  - 350 would *estimate* the error rate to within ±5%.
  - We only need to *show* it is below a pre-set bound, and a one-sided acceptance test does that with 93.
  - A 10% bound would need 46 (c = 1). We chose 5% because the answer key feeds both training and the held-out-family test.

## Models (chosen from untrained results; rule fixed before training)

Selection rule:
- Within each scorer type, keep the latency–tightness frontier points from E1/E5 (F-24, F-26).
- Add the fastest model with the most room to improve.
- Drop models whose interface can't be trained the same way.

| Scorer type | Trained model | Why (untrained result) |
|---|---|---|
| Yes/no | Qwen3-Reranker-0.6B | fastest (28 ms) but over-grants (extra 0.40) → most room to improve |
| Yes/no | Qwen3-Reranker-8B | best yes/no model (extra 0.38; FORTIS task 1 0.454) → upper end |
| Embedding (CAPMAS method) | bge-large retrained on our data with CAPMAS's own training code | separates CAPMAS's method from its training data |
| Embedding (CAPMAS method) | Qwen3-Embedding-0.6B with the same training | CAPMAS's method on a newer encoder |
| LLM | Qwen3-1.7B | small (231 ms), grants nearly everything (extra 0.64) |
| LLM | Qwen3-4B | mid-size (436 ms), already tight (0.09) |
| LLM | Qwen3-8B | current best overall (777 ms); can training improve the best? |
| LLM, large (QLoRA; optional, see below) | Qwen3-30B-A3B | fastest precise model (280 ms), but admit gives no protection (outputs only yes/no). Training can teach "plausible" |

Dropped:
- Reranker-4B: dominated by the 0.6B and 8B.
- Qwen3-0.6B and Phi-4-mini: the 1.7B covers the small tier.
- Laya and CLM: fixed vendor heads.
- gpt-oss-20b and -120b: 2.5–4 s reasoning latency.
- Qwen3-32B: the 30B-A3B covers the large tier.

## Fine-tuning settings

- **Full fine-tuning (all weights) for every model up to 8B.**
  - The trained and untrained versions differ only in training: same bf16 precision, no adapters.
  - Full fine-tuning learns new tasks better than LoRA [M4]. Its extra forgetting doesn't matter for a single-purpose scorer.
  - Memory: about 16 bytes per parameter with AdamW (bf16 weights and gradients, fp32 master copy and two moment estimates).
    - 0.6B: about 10 GB, and 1.7B: about 27 GB, so each fits on one L40S.
    - 4B (about 64 GB) and 8B (about 128 GB) keep the optimizer state in CPU memory (DeepSpeed ZeRO-Offload [M5]; the machine has 1.5 TB RAM). The GPU then holds about 16 GB and 32 GB respectively, plus activations.
- **Qwen3-30B-A3B can't be fully fine-tuned here** (about 480 GB of training state).
  - If included, it is the only QLoRA model [M2].
  - It is evaluated against its own untrained 4-bit version, and also merged into bf16 against the untrained bf16 version, so precision and training are never mixed in one comparison.
- **Starting hyperparameters:**
  - Schedule from ToolPrivBench's SFT [B3]: cosine decay, 3% warmup, 2 epochs, loss on assistant tokens only.
  - Learning rate picked from {5e-6, 1e-5, 2e-5} on the validation split. Never on test.
- **Compute estimate** (training FLOPs ≈ 6 × parameters × tokens [M6]; L40S 362 TFLOPS dense bf16, assuming 30% utilization, and 2× slower when offloading):
  - Token counts:
    - Reranker data: 18k pairs × about 300 tokens × 2 epochs ≈ 11M tokens.
    - LLM data: 1,500 × about 700 tokens × 2 epochs ≈ 2M tokens.
  - Per run, on a free GPU:
    - Reranker-0.6B: about 10 min
    - Reranker-8B: about 3 h (offload)
    - Qwen3-1.7B: about 15 min
    - Qwen3-4B: about 30 min (offload)
    - Qwen3-8B: about 1 h (offload)
    - each embedding model: under 1 h
  - × 3 learning rates on validation, then × 3 seeds for the chosen rate: **about 1.5–2 GPU-days in total.**
- **Targets:**
  - Rerankers: yes/no on each (task, candidate) pair, with the logit of "yes".
  - LLMs: the existing `{required, plausible}` JSON, with "required" = the answer key and "plausible" = its acceptable alternates (the `alternates` field).
  - Embeddings: CAPMAS's contrastive loss and settings [C1].
- Seeds: 3 per trained model. Thresholds are re-tuned on dev as in D-12.

## Evaluation

- Test sets:
  - our frozen 288-item test set;
  - held-out families;
  - FORTIS tasks 1–2 [E1];
  - AuthBench (fs/exec) [B1];
  - mostargate [B2].
  - External sets are evaluation only (licenses: AuthBench CC BY-NC-SA per its paper; mostargate GPL-3.0).
- Same metrics and statistics as D-12/D-20: extra, missed, exact, attacks through after recovery, tasks finished, latency (E5, exclusive GPU). Paired cluster bootstrap with Holm correction.
- Primary comparisons:
  - each trained model vs its untrained version;
  - trained Reranker-0.6B vs untrained Qwen3-8B (the speed question);
  - trained models vs CAPMAS as published.
- Training-data ablation: our data + ASTRA (Apache-2.0) [C2].

## Release

- Dataset under a permissive license, with a datasheet [D1].
- Training scripts and configs go in `bench/`.

## References

- [T1] Task-Conditioned Least-Privilege Learning for Executable Terminal and MCP Agents. arXiv:2608.18351, 2026.
- [B1] Do Coding Agents Understand Least-Privilege Authorization? (AuthBench). arXiv:2605.14859, 2026. github.com/evolvent-ai/Authbench
- [B2] H. B. Noyan. Dynamic Capability Scoping for Enterprise AI Agents: A Synthetic Dataset and Three-Source Permission Architecture. ICML 2026; arXiv:2607.22445. Follow-up: Empirical Evaluation of Task-Based Permission Scoping Architecture for AI Agents, arXiv:2609.15422. Data: github.com/0xballistics/mostargate
- [B3] K. Yang, Y. Bu, J. Yi, Y. Wang, B. Zhou, J. Dai, S. Hu, Y. Yang. When Lower Privileges Suffice: Investigating Over-Privileged Tool Selection in LLM Agents (ToolPrivBench). arXiv:2606.20023, 2026.
- [B4] E. Debenedetti et al. AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents. NeurIPS 2024 Datasets and Benchmarks.
- [C1] R. M. Veski, R. Guerraoui, D. Froelicher. CAPMAS: Capability-Based Delegation of Privileges in Multi-Agent Systems. arXiv:2609.06500, 2026.
- [C2] ASTRA: dataset and generation pipeline for task–scope matching in delegated authorization. arXiv:2510.26702, 2025. github.com/outshift-open/ASTRA
- [E1] FORTIS benchmark. github.com/lili0415/FORTIS-Benchmark (pinned commit in `bench/mbla_bench/fortis.py`)
- [S1] Y. Wang et al. Self-Instruct: Aligning Language Models with Self-Generated Instructions. ACL 2023.
- [S2] Y. Qin et al. ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs. ICLR 2024.
- [S3] Z. Liu et al. APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets. arXiv:2406.18518, 2024.
- [P1] AWS IAM Access Analyzer policy generation (generates policies from CloudTrail access activity). AWS documentation.
- [M1] E. J. Hu et al. LoRA: Low-Rank Adaptation of Large Language Models. ICLR 2022.
- [M2] T. Dettmers et al. QLoRA: Efficient Finetuning of Quantized LLMs. NeurIPS 2023.
- [M3] Y. Zhang et al. Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models. arXiv:2506.05176, 2025.
- [M4] D. Biderman et al. LoRA Learns Less and Forgets Less. TMLR 2024.
- [M5] J. Ren et al. ZeRO-Offload: Democratizing Billion-Scale Model Training. USENIX ATC 2021.
- [M6] J. Kaplan et al. Scaling Laws for Neural Language Models. arXiv:2001.08361, 2020 (training compute ≈ 6ND).
- [D1] T. Gebru et al. Datasheets for Datasets. Communications of the ACM, 2021.
- [D2] O. Sainz et al. NLP Evaluation in trouble: On the Need to Measure LLM Data Contamination for each Benchmark. Findings of EMNLP 2023.
- [D3] C. Zhou et al. LIMA: Less Is More for Alignment. NeurIPS 2023.
- [D4] Zero/one-acceptance (binomial "success-run") sampling plans; e.g. D. C. Montgomery, Introduction to Statistical Quality Control, ch. 15 (lot acceptance sampling).
- [D5] J. Cohen. A Coefficient of Agreement for Nominal Scales. Educational and Psychological Measurement, 1960.
- [D6] J. R. Landis, G. G. Koch. The Measurement of Observer Agreement for Categorical Data. Biometrics, 1977.
- [D7] C. J. Clopper, E. S. Pearson. The Use of Confidence or Fiducial Limits Illustrated in the Case of the Binomial. Biometrika, 1934.

## Implementation (as built; `bench/mbla_bench/synth/`, `bench/data/synth/`)

| Piece | File | Status and checks |
|---|---|---|
| Vocabulary | `data/synth/vocabulary.yaml`, `synth/vocabulary.py` | 52 calls. S3 mappings checked against AWS's service reference v1.4: 0 problems, and injected wrong mappings are caught. Each call adds `net:connect` for its host. Conditional S3 actions (tags, ACL) are added only when the call uses that feature, because AWS lists every action an operation *may* need. |
| Labeler | `synth/label.py` | Key = minimal set covering every logged permission. Training label = for each key permission, the narrowest candidate covering it (candidates built exactly like `mbla.Candidates`; the Python port matches Go on 408/408 items). **Validation: call plans for the 17 templates reproduce the human-reviewed reference on 408/408 benchmark items.** Before narrowing to candidates, 14/17 template keys match exactly; the other 3 are strictly narrower (a file inside `/artifacts` instead of the directory). |
| Mock execution | `synth/execute.py` | Per-argument format rules (GitHub, S3 and Slack naming rules; sandbox paths limited to /workspace, /artifacts and /tmp) plus grounding: every resource a call touches must appear in the task text or arguments. Passes all 408 benchmark items and rejects malformed or ungrounded plans. |
| Sender holdings | `synth/holdings.py` | narrow: up to one sibling operation per needed capability (same resource) plus one same-operation-elsewhere permission. medium: needed and sibling operations widened to the container (repository, bucket prefix, or all docs/channels). broad: widened to organisation or bucket plus `net:connect:*`, `fs:r:*`, `exec:run:*`. Runtime holdings as in the benchmark. Siblings are operations sharing a named resource template (`{doc}`, `{channel}`, `{owner}/{repo}#{number}`, …). |
| Families | `data/synth/families.yaml`, `synth/holdout.py` | 40 families (BC-1 15, BC-2 13, BC-3 12). Held out with seed "D-21", 3/3/2 per workflow: ci-diagnose, issue-reply, pr-review, cleanup, promote, upload-many, doc-combine, slack-post. |
| Names | `data/synth/names.yaml` | Disjoint from the benchmark pools (checked: 0 shared values). |
| Writer prompt | `synth/write.py` | 5 tasks per request, constrained by a JSON schema (call names limited to the family's calls). Prompt text: report Appendix A. |
| Judge prompt | `synth/judge.py` | completes / unneeded / ambiguous. Accept only if both judges return completes = true, unneeded = [] and ambiguous = false. |
| Still to build | — | injection writer, 8-gram decontamination, near-duplicate filter, assembly and splits, audit sheet, training scripts. |
