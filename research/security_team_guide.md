# Choosing a permission helper for BoundClaw

Results as of 2026-11-10. Every number here comes from our final test: 192 tasks in 8 task families that no helper or
setting was tuned on, run once. Full detail: `findings.md` F-31; decisions D-54 to D-67.

## What the helper does

When one agent hands a task to another, the helper reads the task and picks which permissions to grant from a list.
It also names a few backup permissions the receiving agent may ask for later. We measure two things:

- **Covered:** how often the receiving agent ends up able to do the task (directly or by asking for a backup at most
  three times). Higher is better: a miss means the task fails.
- **Unneeded:** how much authority was granted beyond what the task needs, on a scale where granting everything = 1.0.
  Lower is better.

## Recommended

| | Helper | Covered | Unneeded | Typical / slow answer | Hardware |
|---|---|---|---|---|---|
| **Default** | Qwen3-4B, as released (no extra training) | 94% | 0.21 | 0.3 s / 0.7 s | 1 GPU (L40S) |
| **If fewer failed tasks matter more than speed** | gpt-oss-120b | 97% | 0.21 | 2.6 s / 5.3 s | 2 GPUs |

Qwen3-4B was chosen by a rule fixed before the final test (lowest unneeded authority on practice tasks while covering
as much as granting everything). It cuts unneeded authority by 80% compared with granting everything (statistically
significant). gpt-oss-120b grants the same amount of unneeded authority and fails fewer tasks, but is about eight
times slower and needs two GPUs.

"Slow answer" is the time 1 answer in 20 exceeds.

## All helpers we tested

| Helper | Covered | Unneeded | Typical / slow answer | Notes |
|---|---|---|---|---|
| Qwen3-4B | 94% | 0.21 | 0.3 s / 0.7 s | recommended default |
| gpt-oss-120b | 97% | 0.21 | 2.6 s / 5.3 s | recommended alternative; 2 GPUs |
| Qwen3-8B | 95% | 0.28 | 0.7 s / 1.5 s | |
| Qwen3-30B | 83% | 0.22 | 0.2 s / 0.4 s | 2 GPUs; misses more tasks |
| Qwen3-1.7B | 84% | 0.24 | 0.1 s / 0.4 s | |
| Qwen3-Reranker-8B | 100% | 0.61 | 0.1 s / 0.3 s | never misses, but grants a lot |
| Qwen3-4B, fine-tuned by us | 82-84% | 0.07-0.09 | similar to Qwen3-4B | least authority, but misses about 1 task in 6; see below |
| CAPMAS (published method) under our rules | 96% | 0.75 | 0.02 s / 0.03 s | |
| CAPMAS retrained on our data | 87-95% | 0.43-0.62 | similar to CAPMAS | |
| Grant everything the parent has | 83% | 1.00 | — | today's behaviour without a helper |

Other fine-tuned models (1.7B, 8B, two rerankers) also grant little but cover only 40-84% of tasks.

## Why we do not recommend the fine-tuned helper

- On practice tasks it covered about as many tasks as the plain model; on the final test it dropped to 82-84%.
- It was trained to answer with the two lists in the opposite order from the one BoundClaw's code asks for. All
  numbers above use BoundClaw's order. If your adapter asks in the other order, it grants about six times more
  unneeded authority (checked on practice tasks). We have asked BoundClaw which order the adapter uses.

## Under attack

We planted instructions in task text that try to get an extra permission granted.

- With the planted instruction alone, the targeted permission was reachable 87% of the time (31% with no instruction).
  An attacker who also searches for extra text with full access to the model reaches 95%.
- None of the attacks significantly reduced the helper's overall benefit, and the backup list keeps an attacker
  inside the helper's chosen set: under the old rule (backups from everything the parent holds), attacks reached
  their target far more often (statistically significant).
- So: the helper reduces authority, but it is not a defence against a prompt-injected task on its own. The
  delegator's ceiling still bounds what can ever be granted.

## Settings to use

- Qwen3-4B, revision `1cfa9a7208912126459214e8b04321603b3df60c`, served by vLLM with JSON-schema output (xgrammar),
  temperature 0, thinking off. Grant above score 0.8, backups above 0.2. At most 3 backup requests.
- gpt-oss-120b, revision `b5c939de8f754692c1647ca79fbf85e8c1e70f8a`, same settings, 4,096 output tokens, two GPUs.
- Exact commands: `bench/config/models.yaml`.

## Limits of these results

- No helper reaches the 98% coverage goal; the main cause is that a folder missing from the first grant cannot be
  asked for later (F-30).
- The final test has 8 task families, so differences between similar helpers (for example Qwen3-4B vs Qwen3-8B)
  are not statistically settled.
- Answers were measured on our L40S GPUs; speed will differ on other hardware.
