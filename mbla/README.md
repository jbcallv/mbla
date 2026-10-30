# mbla

Policy inference and recovery admission for BoundClaw delegations. Standard library only.

```
go get github.com/jbcallv/mbla/mbla
```

## Delegator side

```go
request := mbla.Request{
	Operation: "github.triage",
	Receiver:  mbla.Receiver{Name: "triage-agent"},
	Text:      taskText,
	Named:     []string{"github:acme/web/issues/42/"}, // resources the context names; never shown to the scorer
}
proposal, err := mbla.Propose(ctx, scorer, request, holdings, mbla.Thresholds{Initial: 0.8, Admit: 0.2})
if err := mbla.CheckAttenuation(proposal.Initial, holdings); err != nil {
	return err
}
send(proposal.Initial)

if err := mbla.CheckAttenuation(installed, holdings); err != nil {
	return err
}
releaseCredentials(installed.Capability())
recovery := &mbla.Recovery{Holdings: holdings, Admit: proposal.Admit, Ceiling: receiverCeiling, Mode: mbla.Admitted, Cap: 3}
```

On a recovery request:

```go
switch recovery.Decide(mbla.RecoveryRequest{TaskID: taskID, Permission: requested}) {
case mbla.Granted:
	grant(requested)
default:
	refuse()
}
```

## Receiver side

The receiver rejects a proposal whose destinations or volumes are not within its ceiling (C is bounded by the parent only).

```go
if !mbla.WithinCeiling(proposal, ceiling) {
	return reject(proposal)
}

if ceiling.Covers(requested) {
	askDelegator(requested)
}
if granted && mbla.NeedsNewSandbox(requested) {
	applyNewPolicy(proposal.Add(requested))
}
```

Turning a denied request into a `Permission` is the enforcement side's job. `NetworkPermission` and `VolumePermission` build correctly formatted permissions from those events. A volume request is always refused (`VolumeFinal`): volumes are granted at delegation only.

## Scorers

| Scorer | Use |
|---|---|
| `mbla.SetOnly{}` | no minimization: the initial grant is all holdings |
| `mbla.ManifestOnly{}` | the manifest intersected with holdings |
| `mbla.Lexical{}` | resources mentioned in the request |
| `&mbla.SystemOne{...}` | any TypeSafe-wire System One endpoint (Jev, or CLM via `clm-serve /v1/systemone`), one yes/no question per candidate |
| `&mbla.DecisionModel{...}` | any yes/no decision model behind a `/score` endpoint (Qwen3-Reranker and Laya via `bench/serve/decision_server.py`) |
| `&mbla.ChatModel{...}` | any OpenAI-compatible chat endpoint |

A scorer is untrusted. Inside BoundClaw, BoundClaw's checker decides what is allowed. MBLA's `CheckAttenuation`, `ApplyCeiling` and `Decide` are advisory and serve the benchmark.

## Permission format

`service:operation:resource`, in BoundClaw's atom forms (`../research/boundclaw_atom_forms.md`):

| Part | Example | Rule |
|---|---|---|
| C | `github:issue.read:acme/web/issues/42/*`, `storage:object.put:acme-staging/web/app.tar.gz/*` | a grant covers every resource under its prefix; resources end in `/` |
| Destination without a parser | `net:connect:example.org:443` | exact host and port |
| Volume | `fs:ro:/workspace/src`, `fs:rw:/artifacts` | whole volume; `rw` covers `ro`; local receivers only |

Hosts with a parser (S3, GitHub, Docs, Slack) follow C and are never candidates. See `../research/final_methodology.md` §12.

## Commands

```
go test ./...
go build -o bin/mbla ./cmd/mbla
bin/mbla check -child child.json -parent parent.json
```
