# Alignment with the BoundClaw paper

How MBLA maps onto `paper-2.pdf` (Sep 28 2026 draft), and where it deliberately differs. MBLA is the policy-inference and recovery-admission component; the enforcement layer (tunnel, sandbox, attestation) and the paper itself are out of scope.

## Design (paper §3–§4)

| Paper | MBLA | Status |
|---|---|---|
| Each delegation carries a pair (C, P), P = (N, F, X); order ⪯ is component-wise (§3.1) | `Policy` is one permission set; `Capability()`, `Network()`, `Filesystem()`, `Executables()` are the components. Coverage never crosses kinds, so this equals the component-wise order (D-02) | aligned |
| G1: child ⪯ parent, child ⊑ C_ceil, child ⊑ P_ceil (§3.2) | `CheckAttenuation(child, parent)` on the delegator; `ApplyCeiling(proposal, ceiling)` on the receiver | aligned |
| Receiver ceilings are checked locally; the delegator never learns them (§4.2) | `ApplyCeiling` runs on the receiver; the delegator only sees what was installed | aligned |
| Receiver *rejects* a proposal that exceeds its ceiling (§4.2) | `ApplyCeiling` clips to `proposal ∩ ceiling` and reports `dropped`; a caller that wants rejection rejects when `dropped` is non-empty (D-03) | deviation, configurable |
| Policy inference is untrusted; the enforcement layer builds the proposal and checks it (§3.3, §4.2) | `Propose` only picks from `Candidates`, which come from the delegator's holdings; `CheckAttenuation` reruns on its output | aligned |
| Task introspection: operation, arguments, delegation history (§4.2) | `Request{Operation, Arguments, Text, History}`; `Describe` renders it identically for every scorer | aligned |
| Operator-signed manifests are hints, outside attestation (§4.2) | `LoadManifest` (ed25519), `Manifest.For`; passed to scorers as context; `ManifestOnly` baseline | aligned |
| Recovery bound Bound_i = C_i ∩ C_ceil; one concrete action per request; grants join the receiver's holdings; per-task cap; logged (§4.2) | `Recovery.Decide`: rejects patterns (`NotConcrete`), enforces `Cap`, requires coverage by current `Holdings`; the receiver checks its ceiling before asking (D-04). `Mode: BoundOnly` is exactly the paper's rule | aligned |
| (not in paper) | `Mode: Admitted` additionally requires the request to be in the scored `Admit` set. Proposed because under the paper's rule a malicious receiver reaches every attack inside `Bound` (F-01; confirmed on test, F-24) | **proposed extension** |
| Recovery for P changes the sandbox (implied) | `NeedsNewSandbox(permission)` tells the enforcement side; applying it is theirs | interface only |

## Evaluation (paper §6)

| Paper | MBLA benchmark | Status |
|---|---|---|
| Workloads BC-1, BC-2 (2 hops), BC-3 (§6.1) | 17 templates over the 5 delegation boundaries; human-reviewed references (κ = 0.85) | aligned |
| AgentDojo external validation (§6.1) | FORTIS used instead (released, minimality ground truth, official metrics); AgentDojo left for later (D-07, D-16) | deviation |
| Reference policy D*_t; atoms; EAC, MAC, RAS, policy size; per component, never micro-averaged; EAC omitted when the denominator is zero (§6.1, §6.3) | `metrics.py` implements exactly these, over the set ⟦C⟧ with witness actions (D-10) | aligned |
| RQ1 checker conformance vs an independent reference; false accept/reject rates (§6.2) | E7: Go checker vs Python set semantics, 14,480 pairs, 0 / 0; mutation test catches a broken checker | aligned |
| RQ2: compare inference against the full-parent and reference endpoints and against each other; adversarial proposals of the second class (§6.3) | E1 (`set-only` = full parent, oracle = reference, 15 inference methods), E9 (injection variants) | aligned |
| RQ3 task completion with Vanilla / reference / inferred (§6.4) | offline: simulated benign success under recovery (E6). Online runs need the enforcement runtime | partial (online is enforcement side) |
| RQ4 attacks: cross-resource, ambient authority, re-delegation, injection, negative control (§6.5) | offline RAS over each item's attack objectives (E6); re-delegation is covered by the checker (E7). Executing attacks needs the runtime | partial (online is enforcement side) |
| RQ5 policy-inference cost: latency, tokens, money, reported apart from enforcement costs (§6.6) | E5: median and tail latency per model on exclusive GPUs; tokens recorded per row | aligned |
| No LLM judge where service state decides (§6.1) | judge used only on prediction-vs-reference disagreements; deterministic metrics stay primary (F-11, D-19) | aligned |
| Configurations Vanilla / Capability-only / Confinement-only / reference / inferred (§6.1) | MBLA supplies the reference and inferred policies; running the five system configurations is the enforcement side's job | interface only |
