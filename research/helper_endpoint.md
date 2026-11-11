# MBLA permission helper: endpoint and usage spec

How BoundClaw calls the hosted permission helper. Updated 2026-11-11 (decision D-72). The hosted helper is now the
fine-tuned Qwen3-Reranker-8B, on a rented GPU. It answers the same request the October client and BoundClaw's
current adapter already send. **The only change for existing callers is the base URL** (section 3). The API key is
not in this file. It is shared separately and must be read from the environment variable `MBLA_API_KEY`; it is the
same key as before.

## 1. What the helper does

When the delegator hands a task to a receiver, the helper reads the task and the candidate permissions (drawn from
what the delegator holds) and returns two lists:

- `required`: granted to the receiver now;
- `plausible`: backups the receiver may ask for later, one at a time, at most 3 requests.

Anything in neither list is never granted. The helper can only choose from the candidates, so its worst answer
equals handing over everything. BoundClaw's own checker and the receiver's ceiling still decide what is allowed.

Inside the server, the reranker scores each candidate from 0 to 1. A score of 0.7 or more makes the candidate
`required`, and from 0.15 up to 0.7 makes it `plausible`. These are this model's cutoffs, tuned on the development
set. With the client's usual `Thresholds{Initial: 0.8, Admit: 0.2}`, the grants are exactly the reranker's grants:
checked on 408 of 408 development tasks.

## 2. Connection

| Setting | Value |
|---|---|
| Base URL | `https://ljhbcrzr9edp5a-8300.proxy.runpod.net/v1` |
| API | `POST {base}/chat/completions` (the mbla chat format), `GET {base}/models` |
| Auth header | `Authorization: Bearer $MBLA_API_KEY` (missing or wrong key: HTTP 401) |
| Model name | `mbla-reranker-8b-tuned`; the old names `mbla-qwen3-4b-tuned` and `Qwen/Qwen3-8B` are accepted and give the same answers |
| Model | Qwen3-Reranker-8B fine-tuned for this task (training seed 1, lowest validation loss) |
| Where it runs | one H100 GPU on Runpod, HTTPS through Runpod's proxy |
| Typical latency | about 0.14 s per call (0.22 s at the 95th percentile), measured from ams1 |

Check that it is reachable:

```bash
curl -s https://ljhbcrzr9edp5a-8300.proxy.runpod.net/v1/models -H "Authorization: Bearer $MBLA_API_KEY"
```

The answer lists the three model names.

## 3. Using the mbla Go library (what BoundClaw's adapter does)

Nothing changes except `Endpoint`. No re-vendoring is needed.

```go
helper := &mbla.ChatModel{
	Endpoint:  "https://ljhbcrzr9edp5a-8300.proxy.runpod.net/v1",
	APIKey:    os.Getenv("MBLA_API_KEY"),
	Model:     "mbla-reranker-8b-tuned", // the old name also works
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
  "model": "mbla-reranker-8b-tuned",
  "messages": [
    {"role": "system", "content": "<any; ignored by this model>"},
    {"role": "user", "content": "Delegated request:\ntask: <task text>\nmanifest: <permission>\n\nCandidate permissions:\n0. <permission>\n1. <permission>\n"}
  ]
}
```

- The server reads only the last message. It must follow the layout above exactly, which is what
  `mbla.ChatModel` writes. That is `Delegated request:`, then the lines of `mbla.Describe(request)`: `task: <text>`,
  then one `manifest: <permission>` per manifest permission, each ending in a newline. Then a blank line,
  `Candidate permissions:`, and one `<index>. <permission>` line per candidate, numbered from 0.
- Other fields (`temperature`, `seed`, `response_format`, `chat_template_kwargs`) are accepted and ignored. The
  answer is deterministic.
- A prompt that does not follow the layout gets HTTP 400; treat it as no handoff.

Response, OpenAI-style: `choices[0].message.content` is a JSON object, for example
`{"plausible":[3],"required":[0,2]}`. Grant `required` now; keep `plausible` as the backup list.

The server also offers `POST {host}/score`: send `{"state": <Describe(request)>, "candidates": [...]}` to
`https://ljhbcrzr9edp5a-8300.proxy.runpod.net/score` and get one score per candidate back. Use cutoffs 0.7 / 0.15
with `mbla.DecisionModel`. This gives the same grants and is not needed by BoundClaw.

## 5. What to expect

Final test, 192 tasks, held out from all development (full report: `research/eval_paper/main.pdf`):

| Helper | Tasks completed | Unneeded authority (0 = none, 1 = everything) | Attack reached its goal (injected tasks) |
|---|---|---|---|
| Reranker-8B fine-tuned, seed 1 (hosted) | 84% | 0.12 | 31% |
| Qwen3-4B fine-tuned, seed 2 (hosted until 2026-11-11) | 82% | 0.07 | 69% |
| Qwen3-4B, not fine-tuned | 94% | 0.21 | 63% |
| Handing over everything | 83% | 1.00 | 81% |

- "Tasks completed" means the receiver could get every permission it needed within 3 backup requests.
- On the 408 development tasks, the hosted server gives the same grants as our benchmark run on 403. The other 5
  differ by rounding between GPU types. Tasks completed, unneeded authority and attack reach are unchanged
  (97.8%, 0.072, 27.0% against 97.8%, 0.073, 26.5%).
- The helper reduces authority but does not by itself stop injected instructions. Keep the ceiling and keep backups
  limited to the helper's list.

## 6. Contact and availability

Server and model questions: Joseph Call. The pod is rented and runs until stopped. Ask before load testing. The old
address `http://172.16.31.10:8300` no longer answers.
