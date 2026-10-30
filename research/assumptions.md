# Assumptions

Scope: MBLA only. Entries about the enforcement side are interface expectations, not work we do.

Things we assumed so work could proceed. Each one is a placeholder until confirmed. When one changes, update the listed files and note it here.

## A-01 · Mount names
- **Assumed:** both sides of every delegation agree on these logical mounts:
  - `/workspace`: the receiver's task working directory (read-write)
  - `/workspace/src`: the checked-out source for build tasks
  - `/artifacts`: build outputs (since D-30 no longer handed between hops: the build reaches deploy-agent through S3)
  - `/secrets`: credentials the receiver holds independently (never granted; attack target)
- **Since D-30:** each is a whole volume (`fs:ro:` or `fs:rw:`), mounted only into local receivers.
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

## A-08 · (superseded by D-30) Request arguments carry resource-shaped values
- **Assumed:** the tunnel or MCP adapter supplies arguments in resource form (e.g. `issue: "acme/web#42"`, `artifact_key: "acme-staging/builds/app.tar"`), not split into owner/repo/number.
- **Why:** `Candidates` turns capability wildcards into concrete permissions by substituting argument values. Joining split arguments is service-specific and left to the adapter.

## A-09 · (superseded by D-28, D-30) Benchmark ceilings are permissive
- **Assumed:** every benchmark receiver has a service-wide ceiling (`github:*:*`, `net:connect:*`, `fs:r:*`, …), so `Bound ≈ parent`.
- **Why:** this isolates the effect of inference. A restrictive-ceiling variant can be added in `delegations.yaml`.

## A-10 · (obsolete since D-26: no executable permissions) Executables are named by absolute path
- **Assumed:** `exec:run:/usr/bin/python3`, not `exec:run:python3`.
- **Why:** matching on the file name alone would let an agent run any file it names `python3`.

## A-11 · Build output bucket
- **Assumed:** build-agent uploads its artifact to `{owner}-builds/{prefix}/{artifact}/` and deploy-agent reads it from there, then puts it to `{owner}-staging/...`. BoundClaw's Oct 28 answer says build-agent writes `storage:object.put:{artifact_key}` and deploy-agent reads it, without naming the bucket; reusing the staging key would make the deploy step a copy onto itself.
- **To confirm with BoundClaw** (not blocking: one line in `bench/data/templates/delegations.yaml` and the bc2 templates).
- **Affects:** `bench/data/templates/`.

## A-12 · S3 resources end in `/`
- **Assumed:** S3 atoms use the same rule as BoundClaw's other parsers: `storage:object.put:acme-staging/web/app.tar.gz/*`, a resource ends in `/` and a grant covers everything under its prefix. BoundClaw's Oct 28 note introduces the rule "as for S3".
- **Affects:** templates; matching is unchanged (`mbla/permission.go`).

## A-13 · Slack channels in task text
- **Assumed:** the delegator names a channel the way Slack encodes a mention, `<#C7A05D5BA|eng-updates>`, so the channel id in the candidate list can be matched to the text. Workspace and channel ids are derived deterministically from the names (`generate.slack_id`).

## A-14 · Decoy websites
- **Assumed:** the two public decoys are `example.org` and `httpbin.org`, chosen so that no reviewer could argue a task needs them (unlike, say, a package registry for a build).

## A-15 · Named resources stand in for the candidate builder's extraction
- **Assumed:** BoundClaw's candidate builder finds the resources the context names and offers a narrower grant under a held prefix. The benchmark simulates this: each task lists, in `request.named`, every resource its text names (the plan's resources and, when injected, the attack's). Helpers never see this list. The validator checks that each listed resource appears in the text.
