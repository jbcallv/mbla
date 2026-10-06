# Research Findings

A running log of findings for MBLA. Entries marked out of scope belong to the paper or the enforcement side. Add new entries at the bottom, and update an entry's status rather than deleting it.

**Status values:**
- `open`: not yet addressed
- `proposed`: we have a fix, not yet in the paper
- `resolved`: in the paper or the code
- `confirmed`: verified by experiment

Paper references are to `paper-2.pdf` (Sep 28 2026 draft).

---

## F-01 · Recovery admitted only against `Bound` makes inference irrelevant for malicious receivers
- **Status:** proposed
- **Source:** §4.2 "Recovering from under-provisioned policy", §3.3 "Malicious receivers"
- **Finding:** Recovery grants any single action inside `Bound_i = C_i ∩ C_ceil`. The paper frames the risk only as reconnaissance. A malicious or injected receiver can instead *request* every attack permission inside `Bound`, up to the cap. Example (BC-1): the parent's token covers private repos, so a request for `github:contents.read:<private-repo>` is inside `Bound` and gets granted. That's the Invariant Labs attack again.
- **Impact:** With a malicious receiver, BoundClaw-inferred leaves as much of the attack surface reachable (RAS) as having no inference. The RQ2/RQ4 claims about inferred policies don't hold under recovery.
- **Action:** Admit recovery only inside `Admit(τ) ∩ Bound`, where `Admit` is scored against the original request. The paper's per-task cap serves as the budget k. Implemented as `Mode = Admitted` (spec §5.4) and measured in E6 (spec §7.5).

## F-02 · The delegator can't compute `Bound` alone
- **Status:** proposed
- **Source:** §4.2 "Policy engine" (the delegator never learns `C_ceil`/`P_ceil`) vs. "Recovering…" (the delegator grants if inside `Bound_i`)
- **Finding:** `Bound_i` needs the receiver's ceiling, which the paper says stays private to the receiver.
- **Action:** Split the check. The receiver's enforcement layer sends a recovery request only if its ceiling covers it; the delegator checks its own holdings (and `Admit`). Together this enforces `Bound`. Spec §5.4, §6; property P4.

## F-03 · Filesystem paths aren't globally meaningful across machines
- **Status:** out of scope for MBLA (paper or enforcement side); kept for the record
- **Source:** §3.1 (`P' ⊑ P` component-wise, including F)
- **Finding:** `/workspace` on the delegator and on the receiver are different directories, so comparing F across hops only makes sense for agreed logical mount names.
- **Action:** Define F over named mounts (`/workspace`, `/artifacts`, `/secrets`, …) in §3.1. Needs agreement with the enforcement side.

## F-04 · AWS SigV4 can't be placeholder-substituted
- **Status:** out of scope for MBLA (paper or enforcement side); kept for the record
- **Source:** §4.2 "Credential substitution", BC-2
- **Finding:** SigV4 signs each request with the secret key, so a placeholder key produces an invalid signature. The tunnel would have to re-sign the request, not swap a token.
- **Action:** Check feasibility with the enforcement side. If it isn't feasible, BC-2's credential isn't a "supported format", and the paper should say so.

## F-05 · Recovery for P (N, F, X) isn't specified
- **Status:** out of scope for MBLA (paper or enforcement side); kept for the record
- **Source:** §4.2 ("supplemental credential" covers only C)
- **Finding:** Granting a network, filesystem or executable permission mid-task requires changing the sandbox.
- **Action:** The enforcement side recreates the sandbox with the updated policy (`NeedsNewSandbox`, spec §5.4). Open questions: state carryover, repeated side effects, and cost `c_P` for the E6 cost model.

## F-06 · Inference input is a structured request, not just natural language
- **Status:** resolved (paper §4.2 "Task introspection")
- **Finding:** The tunnel gives inference the operation, arguments and delegation history. Arguments supply the concrete resources that non-generative models (Jev) can't produce.
- **Action:** Candidates are concretized from the arguments (spec §5.5). The input ablation is E3.

## F-07 · The paper's (C, P) order equals one set split by kind
- **Status:** resolved (D-02)
- **Finding:** The covers rule never relates different kinds, so a single permission set gives the same order as component-wise `⪯`. This simplifies the implementation and the proof.
- **Action:** property P0 (spec §9), tested.

## F-08 · The evaluation doesn't measure recovery
- **Status:** out of scope for MBLA (paper or enforcement side); kept for the record
- **Source:** §6.4, §6.5
- **Action:**
  - RQ3: add recovery count, latency and cap hits.
  - RQ4: add "malicious receiver escalates through recovery" (`BoundOnly` vs `Admitted`).
  - RQ2: report RAS after recovery.
  - Spec E6.

## F-09 · Hosted Jev sees decrypted task context
- **Status:** open
- **Source:** §4.2 "Task introspection"; Jev is a hosted API only (TypeSafe AI, early access Sep 2026)
- **Finding:** Using Jev means the enforcement layer sends decrypted request content to a third party. This doesn't affect safety (inference is untrusted), but it's a confidentiality issue. Jev is also closed, so its results may not reproduce.
- **Action:** log the Jev `model` version string on every call (done in `remote.go`). Whether hosted inference is acceptable is a deployment decision outside MBLA.

## F-10 · CLM-v0.1-8B shares its backbone with Qwen3-8B
- **Status:** open (to confirm in E4)
- **Source:** CLM model card (frozen Qwen3-8B plus contrastive state/action heads, Apache 2.0, 2,048-token context)
- **Finding:** This allows a matched comparison of contrastive scoring against generation. Risk: the 2,048-token limit may truncate long delegation histories.
- **Action:** E4. Record truncation rate in E3 and E5. Confirm the head API against the model card before implementing a wrapper (superseded: CLM is called directly via `clm-serve`, D-14).

## F-11 · LLM judge use must stay consistent with the paper
- **Status:** resolved (spec §7.8)
- **Source:** §6.1 "We do not use an LLM judge for outcomes that can be determined from service state."
- **Action:** The judge labels only prediction-vs-reference differences. Adjusted metrics are reported alongside the unadjusted ones, and only if human–judge kappa ≥ 0.6.

## F-12 · Receiver rejects on ceiling violation; clipping may be better
- **Status:** out of scope for MBLA (paper or enforcement side); kept for the record
- **Source:** §4.2 "Policy engine" ("if it fails, the receiver rejects the delegation")
- **Finding:** With inferred proposals, one stray permission outside the ceiling fails the whole delegation. Installing `proposal ∩ ceiling` instead is strictly narrower, so equally safe, and reports what was dropped.
- **Action:** `ApplyCeiling` (spec §5.3), with strict rejection still possible. Decide whether to change the paper's wording.

## F-13 · The paper's §5 Security Evaluation is empty
- **Status:** out of scope for MBLA (paper or enforcement side); kept for the record
- **Action:** none for MBLA. Spec §9 lists the properties the tests check.

## F-14 · The paper's workflows give only ~17 distinct task templates
- **Status:** open
- **Finding:** BC-1, BC-2 and BC-3 support only a few legitimate tasks each. With templates as clusters, the test split has 12 clusters. That's enough for cluster-bootstrap CIs, but they will be wide.
- **Action:** report the CIs honestly and list this under threats to validity. Adding AgentDojo (phase 2) is the main way to widen coverage.

## F-15 · Candidate generation can't concretize N, F or X from wildcards
- **Status:** open
- **Finding:** arguments only name capability resources. If the delegator holds only `net:connect:*`, no candidate names `api.github.com:443`, so inference can only grant the wildcard or nothing. Benchmark parents include the concrete reference permissions (parent = reference + extras), which assumes the delegator's holdings are already concrete for N, F and X.
- **Action:** options are (a) manifests supply concrete N/F/X candidates, or (b) a service→host table in the enforcement layer. Decide before phase 2.

## F-16 · Binary scorers can't separate `Admit` from `Bound` (preliminary, dev split, baselines only)
- **Status:** open (preliminary)
- **Source:** smoke test, `results/tables/dev_recovery.csv` (2026-09-28), cap 3
- **Finding:**
  - For `manifest-only`, RAS goes from 0.00 on the initial grant to 1.00 after recovery under `bound-only`, because every reachable attack is recovered. This is F-01 observed.
  - Under `admitted` it stays at 0.00, but benign success drops to 0.40.
  - With 0/1 scores, the only admit thresholds are "the initial grant" and "everything", so tuning picks everything (≡ `bound-only`).
- **Implication:** the admission fix needs graded, calibrated scores. That's a concrete argument for Jev or CLM over binary baselines and plain generation.
- **Action:** confirm on test once models run (E6).

## F-17 · CLM ships its own server with a Jev-style API
- **Status:** resolved
- **Source:** CLM model card (`clm-serve`, `CLMClient.system_one` with `Noul`/`Choice`/`Score`)
- **Action (as built):** `clm-serve` speaks the TypeSafe wire format (`POST /v1/systemone`), so the Go `SystemOne` scorer calls it directly; no wrapper is needed (D-14).

## F-18 · Task paraphrases were written with Claude's help
- **Status:** open
- **Finding:** template texts were drafted by Claude (Opus 5.5) during implementation. If the evaluated frontier model is a Claude model, phrasing familiarity could favor it.
- **Action:** pick a non-Claude frontier model, or have a human rewrite the test texts before freezing. Mention under threats to validity either way.

## F-19 · Checker conformance holds, and the test catches bugs
- **Status:** confirmed (2026-09-28)
- **Finding:** the Go `CheckAttenuation` matches the independent set-semantics reference on 14,480 pairs (9,640 valid, 4,840 invalid, chains up to depth 8): false accepts 0, false rejects 0. A deliberately broken checker (prefix match without the `/` or `#` boundary) produced 72 false accepts, so the test detects real bugs.
- **Code:** `bench/mbla_bench/conform.py`; `results/tables/conformance.json`.

## F-20 · Reference audit: humans agree; all disagreement is on runtime F/X permissions
- **Status:** open (resolution pending)
- **Date:** 2026-10-02
- **Data:** `bench/data/review/audit_alvi.csv`, `audit_joseph.csv` (185 rows, 17 templates; one example per template). Merged labels in `bench/data/review/audit_labels.csv`; disagreements in `audit_disagreements.csv`.
- **Statistics** (`bench/results/tables/reference_audit.json`, `reference_audit_by_kind.csv`, `reference_audit_by_template.csv`; unclear rows excluded from kappa; CIs from a template-cluster bootstrap with 10,000 resamples):
  - **Human vs human (Alvi vs Joseph):** 169 decided rows; 94.1% agreement; Cohen's κ = 0.853 (95% CI 0.749–0.941). Krippendorff's α (humans) = 0.853.
  - **Alvi vs draft:** κ = 0.839 (0.781–0.895). **Joseph vs draft:** κ = 0.696 (0.620–0.773). α (humans + draft) = 0.757.
  - **Unclear:** Alvi 16 (all on executables), Joseph 0.
  - **Needed counts:** Alvi 49, Joseph 51, draft 77. Humans never marked a permission needed that the draft left out, so every disagreement is the draft including more.
  - **By kind:** capability (C, 74 rows) and network (N, 30 rows) agree 100% across all three raters. Filesystem (F, 44 rows) agrees 66–80%; executables (X, 37 rows) 70–100%, plus all 16 unclear rows.
- **Finding:** what a task needs at the API and network level is unambiguous from its text. The runtime permissions (`exec:run:/usr/bin/python3`, `fs:w:/workspace`) depend on how the receiving agent is built, not on the task. Alvi's notes say this directly ("depends on how the agent talks to GitHub; if it has a built-in tool, Python isn't needed"). This confirms the earlier concern that natural language underdetermines confinement (P).
- **Note:** the draft references were written by Claude, so draft-vs-human κ checks that draft, not inter-rater reliability. The reliability measure is human vs human.
- **Action:** decide how to treat runtime F/X before freezing (options: drop them from references and candidates as receiver-provided baseline, or keep them and report F/X separately as implementation-dependent). Then resolve the remaining task-level F/X rows.
- **Update 2026-10-02:**
  - The independent-label statistics are frozen in `bench/results/tables/reference_audit_independent.json`. Report these. Corrections made after seeing the disagreements go only in the `resolved` column of `audit_disagreements.csv`; raw rater sheets are never edited.
  - Decision: runtime permissions stay in the references (option 2: report F/X separately as implementation-dependent).
  - Resolved: `bc2-deploy-verify` / `fs:r:/artifacts` → 1 (Joseph's correction).
  - Joseph's labels on `bc3-read-one`, `bc3-read-two` and `bc3-post-one` reflect missing definitions, not task judgment: the sheet never said what `/workspace` is for, or whether receivers run Python. Together with Alvi's 16 unclear executable rows, this shows the audit needs an explicit receiver runtime profile.
- **Resolved 2026-10-02:** all 35 rows adjudicated by rule (D-13): `python3` → 0 (16 rows), `fs:w:/workspace` → 0 (14), `fs:r:/workspace/src` → 1 (3), `make` → 1 (1), `fs:r:/artifacts` → 1 (1). One unanimous human label (`bc2-lint` needs `python3`) was added to that task's reference. Final labels are in `bench/data/review/audit_final.csv` (150 unanimous, 35 resolved, 47 needed); `make review-final` confirms all 185 match the generated references.
  - The adjudication record is `audit_final.csv` (the `source` column). Don't rerun `review-compare` afterwards expecting `audit_disagreements.csv` to keep every resolved row: rows the updated references now agree with drop out of that file.

## F-21 · Test results: E1, E3, E4, E9 (FORTIS pending)
- **Status:** confirmed on test (2026-10-03). Tables: `bench/results/tables/e1_*.csv`, `e3_*`, `e4_*`; curves: `bench/results/figures/e*_operating_curves.pdf`. Thresholds fixed on dev before any test run (`results/thresholds.json`). 95% CIs are a cluster bootstrap over the 12 test templates.
- **Recovery admission (M3/H3) — the headline:**
  - Under the paper's rule (grant anything inside `Bound`), RAS after recovery is 1.00 for every method: a malicious receiver reaches every attack the parent allows.
  - Under `Admitted` (cap 3):
    - qwen3-8b: RAS 0.118 [0.083, 0.168] at 96.9% benign success (−88%, −3.1 points)
    - qwen3-4b: 0.292 at 89.5%
    - gpt-oss-120b: 0.463 at 96.5%
    - gpt-oss-20b: 0.457 at 95.7%
    - qwen3-reranker-8b: 0.500 at 94.4%
  - Methods whose dev tuning set the admit threshold to 0 (qwen3-30b, qwen3-32b, reranker-0.6b, phi-4-mini, qwen3-0.6b) get no protection (RAS 1.00), as F-16 predicted.
  - H3 (≥50% relative RAS reduction at ≤5 points success cost): met for qwen3-8b, gpt-oss-120b and gpt-oss-20b; borderline for reranker-8b (−50% at −5.6 points). Paired tests still to run.
- **Quality (M1), capability component:**
  - The best balance is the mid-size generative models: qwen3-8b (MAC 0.026, EAC 0.083, exact match 0.37), qwen3-4b (0.036 / 0.092), qwen3-30b (0.041 / 0.086).
  - gpt-oss-120b (0.019 / 0.136, 2.3 s) is not better than qwen3-8b (0.8 s). Scale stops paying off around 4–8B.
  - Decision models are 5–40× faster (21–150 ms) but over-grant: reranker-8b EAC 0.38, reranker-4b 0.64, CLM 0.71, Laya 0.85. Zero-shot CLM and Laya are close to granting the whole parent.
- **Input ablation (M4/H4):**
  - Arguments are what lexical matching needs (MAC 0.49 → 0).
  - For CLM, more structure lowers MAC (text 0.17 → args 0.11 → history 0.08 → +manifest 0.03).
  - For qwen3-8b, the manifest halves EAC (0.19–0.21 → 0.085), with MAC flat around 0.02.
  - H4 (arguments matter most) is not supported in general; only for lexical and CLM.
- **Matched backbone (M5), Qwen3-8B used three ways:** generation EAC 0.083 / exact match 0.375; reranker head 0.379 / 0.024; CLM contrastive heads 0.709 / 0.000. On the same weights, generation is far more precise and the yes/no heads trade precision for speed.
- **Injection (E9):** injected task text raises excess for generative models (qwen3-32b 0.15 → 0.40; qwen3-8b 0.18 → 0.27; gpt-oss-120b 0.14 → 0.25) but barely moves decision models, which are already high. The bounds still cap everything at the parent.
- **Latency caveat:** clm-serve caches embeddings by default ("action cache"). E1 latencies are first-pass and valid; E3 and E4 reuse prompts from E1, so CLM's E3/E4 latencies (down to 1.3 ms) are cache hits. Report E1 latency only. Caching is a legitimate CLM deployment feature, but it must be described as such.

## F-22 · Significance of the pre-declared comparisons (spec §7.9)
- **Status:** confirmed (2026-10-03). Tables: `bench/results/tables/significance_*.csv`. Paired cluster bootstrap over the 12 test templates (10,000 resamples), seeds averaged per item, Holm correction within each metric family. Exact match uses McNemar.
- **M3 (recovery), `admitted` vs `bound-only`, cap 3:** RAS after recovery drops significantly (Holm p < 0.001) for:
  - qwen3-8b: −0.88 [−0.92, −0.83]
  - qwen3-4b: −0.71
  - gpt-oss-20b: −0.54
  - gpt-oss-120b: −0.54
  - reranker-8b: −0.50
  - qwen3-1.7b: −0.36
  - reranker-4b: −0.20
  - clm-zs: −0.11 (p = 0.006)
  - **Success cost:** not significant for qwen3-8b (−3.1 points, p_holm = 1.0), gpt-oss-120b (−3.5), reranker-8b (−5.6, p_holm = 0.22), reranker-4b (0) and clm-zs. Significant for gpt-oss-20b (−4.3), qwen3-1.7b (−6.3) and qwen3-4b (−10.5, p_holm = 0.045).
  - Methods tuned to admit everything (admit threshold 0) show no difference by construction.
- **M1, capability EAC vs clm-zs:** significantly lower for every generative model ≥ 4B and gpt-oss (−0.47 to −0.63, p_holm ≤ 0.016). Not significant for the rerankers (−0.31 to −0.33, p_holm = 0.56), Laya, Phi-4-mini, or Qwen3 0.6B/1.7B. **MAC_C differences vs clm-zs are not significant for any method:** with 12 clusters, the study cannot resolve small differences in missed capabilities.
- **M5 (same Qwen3-8B backbone):** generation vs CLM heads: capability EAC −0.63 (p < 0.001), overall MAC +0.05 (p = 0.046). The reranker head vs CLM heads: overall EAC −0.69 (p < 0.001) but overall MAC +0.35 (p < 0.001); the reranker misses many confinement (F/X) permissions.
- **M4:** for qwen3-8b, removing the manifest raises capability EAC by about 0.11–0.12 (all p < 0.001). For lexical, removing arguments raises MAC by 0.49. No other input effect survives Holm correction.

## F-23 · Harness v1 penalized small chat models; fixed in v2 and rerun
- **Status:** fix applied; rerun in progress (2026-10-03).
- **Finding:** on FORTIS, Qwen3-0.6B failed to parse on 523/579 Task-1 and 1,505/1,543 Task-2 queries, and Phi-4-mini on 1,130/1,543 Task-2 queries. Raw outputs show a valid opening (`{"plausible": [0, 2, ...`) followed by endless whitespace, or index arrays repeating one value until the token cap. vLLM's JSON grammar allowed unlimited whitespace and unbounded arrays, so this came from our decoding configuration, not only the models.
- **Fix (harness v2, applies to all 9 chat models):**
  - vLLM `--structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}'`
  - JSON schema arrays bounded by `maxItems` = number of candidates, with item values limited to valid indices (`remote.go: selectionSchema`)
- **Also fixed:** the Qwen3-Reranker server computed logits for every token position; on long FORTIS prompts reranker-8B ran out of memory (361/1,543 Task-2 errors). It now keeps last-token logits only (`logits_to_keep=1`) and scores candidates in chunks of 16. The scores are mathematically identical.
- **Consequence:**
  - All chat models and rerankers are rerun on dev, then re-tuned, then rerun on test and FORTIS.
  - Laya, CLM and the baselines are unaffected and keep their runs.
  - v1 results are archived in `bench/results/archive/harness_v1/` (raw, tables, thresholds, figures). F-21 and F-22 report v1 numbers and will be superseded by v2.

## F-24 · Harness v2 test results (supersede the numbers in F-21 and F-22)
- **Status:** confirmed (2026-10-05). Tables: `bench/results/tables/` (v1 archived in `results/archive/harness_v1/`). Failures: zero for every method except gpt-oss-20b (E1 2–3%, FORTIS Task 2 3.1%: reasoning loops at its 4096-token budget).
- **Recovery (M3), the headline: holds in v2.** Under `bound-only`, RAS after recovery is 1.00 for every method. Under `admitted` (cap 3):
  - qwen3-8b: 0.133 [0.083, 0.203] at 97.2% success (RAS −0.87, p_holm < 0.001; success change not significant)
  - qwen3-4b: 0.292 at 89.5%
  - gpt-oss-20b: 0.471 at 96.3%
  - gpt-oss-120b: 0.488 at 95.6%
  - qwen3-reranker-8b: 0.500 at 94.4%
  - Admit threshold 0 again gives no protection for qwen3-30b, qwen3-32b, reranker-0.6b, phi-4-mini and qwen3-0.6b.
- **Quality (M1) changes vs v1:**
  - qwen3-32b-awq improves sharply (capability EAC 0.240 → 0.061, exact match 0.39) and is now the most precise model. Its v2 dev tuning picked initial threshold 1.0 instead of 0.5.
  - The small models no longer fail to parse, but now grant nearly everything (qwen3-0.6b EAC 0.745, phi-4-mini 0.794; FORTIS over-privilege ≈ 1.0). Their v1 "failures" were hiding over-granting.
  - Every other method changed by ≤ 0.02.
- **FORTIS Task 1 exact match:** gpt-oss-120b 0.473, qwen3-30b 0.454, qwen3-reranker-8b 0.454, gpt-oss-20b 0.446, qwen3-4b 0.428, qwen3-32b 0.415, reranker-4b 0.397, qwen3-8b 0.359, CLM 0.178, Laya 0.071. The reranker-8B matches 30B–120B generators here.
- **FORTIS Task 2 (tool selection) is hard for everyone:** best exact match is gpt-oss-120b 0.290, then qwen3-32b 0.214. Decision models with thresholds from our dev either abstain (reranker-8B no-action 0.43) or over-grant (CLM, Laya over-privilege ≈ 1.0). Thresholds don't transfer across domains.
- **E3:** for qwen3-8b, the manifest lowers capability EAC from about 0.23 to 0.089. **E4:** generation (EAC 0.090, exact match 0.33) ≫ reranker head (0.379, 0.02) ≫ CLM heads (0.709, 0.00) on the same Qwen3-8B weights.
- **Latency:** v2 runs shared GPUs (D-18), so their latency is not used; E5 is pending exclusive GPUs.

## F-25 · LLM judge (E8): labels and adjusted metrics (human validation pending)
- **Status:** judge done 2026-10-05; human validation pending (150-case sheet `bench/data/review/judge_sample.csv`).
- **Labels (2,240 cases, Llama-3.3-70B):**
  - Missing permissions: 616/616 `necessary-missing`. The judge never said a reference permission was unnecessary, which supports the human-reviewed references.
  - Extras: 867 `unnecessary`, 547 `scope-too-broad`, 57 `equivalent-alternative`, 153 `necessary-missing`.
  - The last group misuses a missing-direction label on extras. It means the judge thinks the task needs the permission, i.e. either a reference gap or a judge error. Per the pre-registered rule it does **not** reduce excess; the human sample will show which it is.
- **Adjusted metrics** (`results/tables/e1_judge_adjusted.json`): capability EAC drops by only 0.01–0.03 for every method, MAC barely moves, and exact match rises by up to 0.02. **Rankings are unchanged.** The deterministic results are robust to reasonable alternative grants.
- These count only if human–judge κ ≥ 0.6 (D-19).

## F-26 · Latency (E5): every model alone on an exclusive L40S
- **Status:** confirmed (2026-10-06). 60 test items (5 per template), seed 0, warm-up 5; raw in `bench/results/raw/e5/` (release asset), plotted in `plots/out/quality_latency.pdf`.
- **Median (p95) latency per delegation:**
  - Laya: 26 (39) ms
  - qwen3-reranker-0.6b: 28 (69) ms
  - clm-zs: 91 (188) ms
  - qwen3-reranker-4b: 118 (257) ms
  - qwen3-0.6b: 132 (394) ms
  - qwen3-reranker-8b: 187 (415) ms
  - qwen3-1.7b: 231 (412) ms
  - qwen3-30b-a3b: 280 (413) ms
  - phi-4-mini: 382 (703) ms
  - qwen3-4b: 436 (829) ms
  - qwen3-8b: 777 (1,149) ms
  - qwen3-32b-awq: 829 (1,078) ms
  - gpt-oss-120b: 2,538 (4,524) ms
  - gpt-oss-20b: 4,112 (10,052) ms
- **Reading:**
  - Qwen3-30B-A3B (3B active parameters) is the fastest of the precise models: capability EAC 0.073 at 280 ms. That's about 3× faster than Qwen3-8B (0.086, 777 ms) with similar precision; recovery admission doesn't help it, though (admit threshold 0).
  - gpt-oss models pay for reasoning: gpt-oss-20b is slower than gpt-oss-120b because it reasons longer per answer.
- CLM's server caches action embeddings within a run; its numbers include that warm cache, as in deployment.
