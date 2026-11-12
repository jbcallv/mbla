# MBLA permission helper: endpoint and usage spec

How BoundClaw calls the hosted permission helper. Updated 2026-11-12 (decision D-75). The hosted helper is now
Qwen3-4B as released, not fine-tuned: the model the paper recommends. Fine-tuned models fit our task data closely and
did worse on tasks unlike it; the released model reads unfamiliar tasks better. Same address, same request, same key:
**existing callers change nothing** (section 3). The API key is
not in this file. It is shared separately and must be read from the environment variable `MBLA_API_KEY`; it is the
same key as before.

## 1. What the helper does

When the delegator hands a task to a receiver, the helper reads the task and the candidate permissions (drawn from
what the delegator holds) and returns two lists:

- `required`: granted to the receiver now;
- `plausible`: backups the receiver may ask for later, one at a time, at most 3 requests.

Anything in neither list is never granted. The helper can only choose from the candidates, so its worst answer
equals handing over everything. BoundClaw's own checker and the receiver's ceiling still decide what is allowed.

The model reads mbla's fixed instructions, the task and the numbered candidates, and answers the two lists as
JSON, constrained to mbla's answer format. The client's usual `Thresholds{Initial: 0.8, Admit: 0.2}` grant exactly
those lists.

## 2. Connection

| Setting | Value |
|---|---|
| Base URL | `https://ljhbcrzr9edp5a-8300.proxy.runpod.net/v1` |
| API | `POST {base}/chat/completions` (the mbla chat format), `GET {base}/models` |
| Auth header | `Authorization: Bearer $MBLA_API_KEY` (missing or wrong key: HTTP 401) |
| Model name | `mbla-qwen3-4b`; the names `Qwen/Qwen3-4B`, `mbla-reranker-8b-tuned`, `mbla-qwen3-4b-tuned` and `Qwen/Qwen3-8B` are accepted so older clients keep working, and all give this model's answers |
| Model | Qwen3-4B as released (revision `1cfa9a72`), not fine-tuned, served by vLLM 0.30.0 with the benchmark's settings |
| Where it runs | one H100 GPU on Runpod, HTTPS through Runpod's proxy |
| Typical latency | about 0.19 s per call (0.29 s at the 95th percentile), measured from ams1 |

Check that it is reachable:

```bash
curl -s https://ljhbcrzr9edp5a-8300.proxy.runpod.net/v1/models -H "Authorization: Bearer $MBLA_API_KEY"
```

The answer lists the five model names.

## 3. Using the mbla Go library (what BoundClaw's adapter does)

Nothing changes except `Endpoint`. No re-vendoring is needed.

```go
helper := &mbla.ChatModel{
	Endpoint:  "https://ljhbcrzr9edp5a-8300.proxy.runpod.net/v1",
	APIKey:    os.Getenv("MBLA_API_KEY"),
	Model:     "mbla-qwen3-4b", // the old names also work
	Seed:      0,
	ExtraBody: map[string]any{"chat_template_kwargs": map[string]any{"enable_thinking": false}},
	Client:    &http.Client{Timeout: 45 * time.Second},
}

proposal, err := mbla.Propose(ctx, helper, request, holdings,
	mbla.Thresholds{Initial: 0.8, Admit: 0.2})
if err != nil {
	// fail closed: no handoff
}
send(proposal.Initial) // grant now

recovery := &mbla.Recovery{
	Holdings: holdings,
	Admit:    proposal.Admit, // backups come only from the helper's lists
	Ceiling:  receiverCeiling,
	Mode:     mbla.Admitted,
	Cap:      3,
}
```

Leave `Glossary` empty. Keep `Mode: mbla.Admitted`: allowing requests for anything the delegator holds lets attacks
reach their target far more often. The full delegator and receiver flow is in `mbla/README.md`.

## 4. Raw HTTP, if not using the library

`POST https://ljhbcrzr9edp5a-8300.proxy.runpod.net/v1/chat/completions` with headers
`Content-Type: application/json` and `Authorization: Bearer $MBLA_API_KEY`:

```json
{
  "model": "mbla-qwen3-4b",
  "messages": [
    {"role": "system", "content": "<mbla's fixed instructions>"},
    {"role": "user", "content": "Delegated request:\ntask: <task text>\nmanifest: <permission>\n\nCandidate permissions:\n0. <permission>\n1. <permission>\n"}
  ]
}
```

- This model reads the whole conversation, so send exactly what `mbla.ChatModel` sends: its fixed instructions as
  the system message, its user message layout, and its answer schema (keys sorted) in `response_format`. Results hold
  only for that request. Using the library is the safe route.
- Decoding is deterministic (seed 0, no thinking).

Response, OpenAI-style: `choices[0].message.content` is a JSON object, for example
`{"plausible":[3],"required":[0,2]}`. Grant `required` now; keep `plausible` as the backup list.

## 5. What to expect

Final test, 192 tasks, held out from all development (full report: `research/eval_paper/main.pdf`):

| Helper | Tasks completed | Unneeded authority (0 = none, 1 = everything) | Attack reached its goal (injected tasks) |
|---|---|---|---|
| Qwen3-4B, not fine-tuned (hosted) | 94% | 0.21 | 63% |
| Reranker-8B fine-tuned, seed 1 (hosted 2026-11-11 to 11-12) | 84% | 0.12 | 31% |
| Qwen3-4B fine-tuned, seed 2 (hosted until 2026-11-11) | 82% | 0.07 | 69% |
| Handing over everything | 83% | 1.00 | 81% |

- "Tasks completed" means the receiver could get every permission it needed within 3 backup requests.
- On the 408 development tasks, the hosted server gives the same grants as our benchmark run on 370. The other 38
  differ by rounding between GPU types (our three benchmark seeds agree with each other on all 408). Tasks
  completed, unneeded authority and attack reach are unchanged (89.2%, 0.106, 57.6% against 89.2%, 0.104, 58.0%).
- The helper reduces authority but does not by itself stop injected instructions. Keep the ceiling and keep backups
  limited to the helper's list.

## 6. Contact and availability

Server and model questions: Joseph Call. The pod is rented and runs until stopped. Ask before load testing. The old
address `http://172.16.31.10:8300` no longer answers.
