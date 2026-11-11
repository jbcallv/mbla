# MBLA permission helper: endpoint and usage spec

How BoundClaw calls the hosted permission helper. Updated 2026-11-11 (decision D-70): the hosted helper is now the
fine-tuned Qwen3-Reranker-8B, replacing the fine-tuned Qwen3-4B of D-68. **The request format changed.** See section 7.
The API key is not in this file. It is shared separately and must be read from the environment variable
`MBLA_API_KEY`.

## 1. What the helper does

When the delegator hands a task to a receiver, the helper reads the task and the candidate permissions (drawn from
what the delegator holds). It gives each candidate a score from 0 to 1. The delegator applies two cutoffs:

- score ≥ 0.7: granted to the receiver now;
- score ≥ 0.15: a backup the receiver may ask for later, one at a time, at most 3 requests.

Anything below 0.15 is never granted. The helper can only score the candidates it is given, so its worst answer
equals handing over everything. BoundClaw's own checker and the receiver's ceiling still decide what is allowed.

## 2. Connection

| Setting | Value |
|---|---|
| Base URL | `http://172.16.31.10:8300` (host `ams1`); no `/v1` |
| API | `POST {base}/score` (not OpenAI-compatible); `GET {base}/health` |
| Auth header | `Authorization: Bearer $MBLA_API_KEY` (missing or wrong key: HTTP 401) |
| Model | Qwen3-Reranker-8B fine-tuned for this task (training seed 1, lowest validation loss) |
| Cutoffs | grant now at 0.7, backup at 0.15 |
| Context limit | 8,192 tokens per candidate (task + one permission) |
| Typical latency | about 0.13 s per call (0.30 s at the 95th percentile) |

Check that it is reachable:

```bash
curl -s http://172.16.31.10:8300/health
```

The answer is `{"status": "ok"}`.

## 3. Recommended: use the mbla Go library

The library (`github.com/jbcallv/mbla/mbla`) builds the exact request the helper was evaluated with. The `APIKey`
field on `DecisionModel` was added on 2026-11-11, so re-vendor `mbla/` at that commit or later. Settings go in three
places.

### 3.1 Create the helper once

```go
helper := &mbla.DecisionModel{
	Label:    "mbla-reranker-8b-tuned",
	Endpoint: "http://172.16.31.10:8300",
	APIKey:   os.Getenv("MBLA_API_KEY"),
	Client:   &http.Client{Timeout: 45 * time.Second},
}
```

Leave `Glossary` empty: the helper was evaluated on bare permission strings, without descriptions.

### 3.2 On each delegation: ask what to grant

```go
request := mbla.Request{
	Operation: "github.triage",
	Receiver:  mbla.Receiver{Name: "triage-agent"},
	Text:      taskText,                              // the task text the delegator wrote
	Manifest:  receiverManifest,                      // optional: what the receiver's operator says it needs
	Named:     []string{"github:acme/web/issues/42/"}, // resources the context names; never shown to the helper
}
proposal, err := mbla.Propose(ctx, helper, request, holdings,
	mbla.Thresholds{Initial: 0.7, Admit: 0.15})
if err != nil {
	// fail closed: no handoff
}
send(proposal.Initial) // grant now
```

- `holdings` is what the delegator holds; candidates are built from it by the library, not by the model.
- Keep `Initial: 0.7` and `Admit: 0.15`. They were tuned for this model on the development set, and they are the
  values evaluated. The old 0.8 / 0.2 belonged to the chat model.
- On any error (timeout, wrong number of scores), do not hand off.

### 3.3 Set up later requests

Unchanged:

```go
recovery := &mbla.Recovery{
	Holdings: holdings,
	Admit:    proposal.Admit,    // backups come only from the helper's list
	Ceiling:  receiverCeiling,
	Mode:     mbla.Admitted,
	Cap:      3,                 // at most 3 requests per task
}

switch recovery.Decide(mbla.RecoveryRequest{TaskID: taskID, Permission: requested}) {
case mbla.Granted:
	grant(requested)
default:
	refuse()
}
```

## 4. Raw HTTP, if not using the library

Results match the evaluation only if every field below is the same.

### 4.1 Request

`POST http://172.16.31.10:8300/score` with headers `Content-Type: application/json` and
`Authorization: Bearer $MBLA_API_KEY`.

```json
{
  "state": "task: <task text>\nmanifest: <permission>\nmanifest: <permission>\n",
  "candidates": [
    "github:issue.read:acme/web/issues/42/*",
    "github:issue.comment:acme/web/issues/42/*",
    "net:connect:example.org:443"
  ]
}
```

- `state`: one line `task: <text>`, then one line `manifest: <permission>` per manifest permission. Every line ends
  in a newline, and lines with an empty value are left out. This is `mbla.Describe(request)`.
- `candidates`: the candidate permissions as `service:operation:resource` strings, built as by `mbla.Candidates`.
  There are no indices, no system prompt, no answer schema and no key-order concern.

### 4.2 Response

```json
{"model": "<model path>@default", "scores": [0.98, 0.31, 0.02]}
```

`scores` has one number per candidate, in the same order. Grant those ≥ 0.7 now, and keep those ≥ 0.15 as the
backup list. A wrong number of scores, or any HTTP error, means no handoff.

## 5. What to expect

Final test, 192 tasks, held out from all development (full report: `research/eval_paper/main.pdf`):

| Helper | Tasks completed | Unneeded authority (0 = none, 1 = everything) | Attack reached its goal (injected tasks) |
|---|---|---|---|
| Reranker-8B fine-tuned, seed 1 (hosted) | 84% | 0.12 | 31% |
| Qwen3-4B fine-tuned, seed 2 (hosted until 2026-11-11) | 82% | 0.07 | 69% |
| Qwen3-4B, not fine-tuned | 94% | 0.21 | 63% |
| Handing over everything | 83% | 1.00 | 81% |

- "Tasks completed" means the receiver could get every permission it needed within 3 backup requests.
- The helper reduces authority but does not by itself stop injected instructions. Keep the ceiling and keep backups
  limited to the helper's list.

## 6. Contact

Server and model questions: Joseph Call. The server runs until stopped; ask before load testing.

## 7. What changed from the Qwen3-4B endpoint (for existing callers)

| | Before (Qwen3-4B, D-68) | Now (Reranker-8B) |
|---|---|---|
| Go type | `mbla.ChatModel` | `mbla.DecisionModel` (re-vendor for `APIKey`) |
| URL | `http://172.16.31.10:8300/v1/chat/completions` | `http://172.16.31.10:8300/score` |
| Body | OpenAI chat request with JSON schema | `{"state", "candidates"}` |
| Answer | `required` / `plausible` index lists | one score per candidate |
| Cutoffs | `Thresholds{Initial: 0.8, Admit: 0.2}` | `Thresholds{Initial: 0.7, Admit: 0.15}` |
| Unchanged | candidates, `Named`, the recovery settings, the API key | |
