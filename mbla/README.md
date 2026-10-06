# mbla

Policy inference and recovery admission for BoundClaw delegations. Standard library only.

```
go get github.com/jbcallv/mbla/mbla
```

## Delegator side

```go
request := mbla.Request{Operation: "github.triage", Arguments: map[string]string{"issue": "acme/web#42"}, Text: taskText}
proposal, err := mbla.Propose(ctx, scorer, request, holdings, mbla.Thresholds{Initial: 0.8, Admit: 0.2})
if err := mbla.CheckAttenuation(proposal.Initial, holdings); err != nil {
	return err
}
send(proposal.Initial)

if err := mbla.CheckAttenuation(installed, holdings); err != nil {
	return err
}
releaseCredentials(installed.Capability())
recovery := &mbla.Recovery{Holdings: holdings, Admit: proposal.Admit, Mode: mbla.Admitted, Cap: 3}
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

```go
installed, dropped := mbla.ApplyCeiling(proposal, ceiling)

if ceiling.Covers(requested) {
	askDelegator(requested)
}
if granted && mbla.NeedsNewSandbox(requested) {
	applyNewPolicy(installed.Add(requested))
}
```

Turning a denied request into a `Permission` is the enforcement side's job. `NetworkPermission`, `FilePermission` and `ExecPermission` build correctly formatted permissions from those events.

## Scorers

| Scorer | Use |
|---|---|
| `mbla.SetOnly{}` | no minimization: the initial grant is all holdings |
| `mbla.ManifestOnly{}` | the manifest intersected with holdings |
| `mbla.Lexical{}` | resources mentioned in the request |
| `&mbla.SystemOne{...}` | any TypeSafe-wire System One endpoint (Jev, or CLM via `clm-serve /v1/systemone`), one yes/no question per candidate |
| `&mbla.DecisionModel{...}` | any yes/no decision model behind a `/score` endpoint (Qwen3-Reranker and Laya via `bench/serve/decision_server.py`) |
| `&mbla.ChatModel{...}` | any OpenAI-compatible chat endpoint |

A scorer is untrusted. Only `CheckAttenuation`, `ApplyCeiling` and `Decide` decide what is allowed.

## Permission format

`service:operation:resource[?qualifier]`, e.g. `github:issue.read:acme/web#42`, `net:connect:api.github.com:443`, `fs:w:/workspace`, `exec:run:/usr/bin/make`. See `../research/spec.md` §4 for the matching rules.

## Commands

```
go test ./...
go build -o bin/mbla ./cmd/mbla
bin/mbla check -child child.json -parent parent.json
```
