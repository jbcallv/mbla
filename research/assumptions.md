# Assumptions

Scope: MBLA only. Entries about the enforcement side are interface expectations, not work we do.

Things we assumed so work could proceed. Each one is a placeholder until confirmed. When one changes, update the listed files and note it here.

## A-01 · Mount names
- **Assumed:** both sides of every delegation agree on these logical mounts:
  - `/workspace`: the receiver's task working directory (read-write)
  - `/workspace/src`: the checked-out source for build tasks
  - `/artifacts`: build outputs handed between hops
  - `/secrets`: credentials the receiver holds independently (never granted; attack target)
- **Why needed:** filesystem paths are compared across hops (finding F-03).
- **Affects:** `bench/data/universe.json`, `bench/data/templates/`.

## A-02 · (removed) AWS SigV4 handling
- Enforcement side's concern; MBLA no longer parses requests.

## A-03 · Deny events are the enforcement side's job
- **Assumed:** the gVisor fork turns its own deny events into `mbla.Permission` values using `NetworkPermission`, `FilePermission` and `ExecPermission`. Recognizing API requests as permissions is also on the enforcement side.
- **Affects:** `mbla/permission.go` provides `NetworkPermission`, `FilePermission` and `ExecPermission` for formatting only.

## A-04 · Sandbox recreation is out of MBLA's scope
- **Assumed:** when `NeedsNewSandbox` is true, the enforcement side recreates the sandbox with the updated policy. State carryover and cost are theirs to handle.
- **Benchmark:** the recovery cost model uses placeholder costs `c_C = 1`, `c_P = 1` (counts only) until measured.

## A-05 · API hosts
- **Assumed:** real API hostnames (`api.github.com`, `<bucket>.s3.<region>.amazonaws.com`, `docs.googleapis.com`, `slack.com`). If the benchmark uses mock services, only the network permissions in the templates change.

## A-06 · Model APIs
- **Jev:** request body `{state, questions: {id: {type: "noul", instructions}}}`, response `answers[id].noul` as a probability, per the Cloudflare/TypeSafe docs (Sep 2026).
- **CLM:** called directly at `clm-serve`'s `POST /v1/systemone` with the TypeSafe wire format (resolved; D-14).
- **Jev endpoint URL:** unknown until early access is granted; left as TBD in `config/models.yaml`.
- **LLMs:** any OpenAI-compatible `/v1/chat/completions` endpoint that supports `response_format` with a JSON schema (vLLM does).

## A-07 · (removed) request path normalization
- Only mattered for request parsing, which is the enforcement side's job.

## A-08 · Request arguments carry resource-shaped values
- **Assumed:** the tunnel or MCP adapter supplies arguments in resource form (e.g. `issue: "acme/web#42"`, `artifact_key: "acme-staging/builds/app.tar"`), not split into owner/repo/number.
- **Why:** `Candidates` turns capability wildcards into concrete permissions by substituting argument values. Joining split arguments is service-specific and left to the adapter.

## A-09 · Benchmark ceilings are permissive
- **Assumed:** every benchmark receiver has a service-wide ceiling (`github:*:*`, `net:connect:*`, `fs:r:*`, …), so `Bound ≈ parent`.
- **Why:** this isolates the effect of inference. A restrictive-ceiling variant can be added in `delegations.yaml`.

## A-10 · Executables are named by absolute path
- **Assumed:** `exec:run:/usr/bin/python3`, not `exec:run:python3`.
- **Why:** matching on the file name alone would let an agent run any file it names `python3`.
