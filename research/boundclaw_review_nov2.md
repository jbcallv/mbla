# BoundClaw review of the Oct 29 methodology (Nov 2, verbatim)

Received from BoundClaw's security lead via Joseph on 2026-11-02. Third-party text, kept as received. Acted on in D-33.

---

# Nov 2 - Review of the methodology of Oct 29

The plan looks good. It matches what we agreed on Oct 27–28, and the training study (§7) is sound. Three updates, from a multi-hop change on our side (Nov 1–2) and from how our adapter calls the helper.

| # | Update | Why |
| --- | --- | --- |
| 1 | Table 1 "Deployment": the root-task rule applies at depth 1 only. At depth ≥ 2 (bc2-deploy) the hop's own layer calls the helper once, with no root task | Each hop's layer now runs its own adapter; the root runs none |
| 2 | Table 1 "Task context": drop "upstream context" and "receiver identity and kind". The helper gets the task text and the manifest lines | Our adapter sends nothing else to the model |
| 3 | §7: train the generative helpers on our exact output schema, {required: \[i\], plausible: \[i\]}, under the call settings on the right. The per-candidate scorers are offline-only: our adapter has no scorer for them | Our adapter calls an OpenAI-compatible chat endpoint with a strict json\_schema, 1024 output tokens, 45 s. It requests thinking off; if a helper needs thinking on, say so |

---

Follow-up from Joseph (2026-11-02): the numbered candidate list carries no description next to each permission.
