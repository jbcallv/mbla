# mbla

Task-scoped permission inference for BoundClaw.

When one agent hands a task to another, the receiver should get only the permissions that task needs. mbla works out that set. It picks from what the delegating agent already holds, so it can never grant more than the parent has, and the receiver's own limits are applied on top. If the receiver gets blocked partway through, mbla also decides whether its request for the missing permission should be granted.

## Using it

The Go package lives in `mbla/` and only uses the standard library:

```go
import "github.com/jbcallv/mbla/mbla"
```

See [`mbla/README.md`](mbla/README.md) for the full delegation flow, with and without a model.

## What's here

- `mbla/`: the package the gVisor fork imports
- `bench/`: the benchmark used to evaluate it (data, model serving, metrics)
- `plots/`: gnuplot scripts for the figures
- `report/`: a short write-up of the results (CI builds the PDF on every push)
- `research/`: design notes, decisions, findings, and how it lines up with the paper

## Results in short

- Under the paper's recovery rule, a compromised receiver could reach every attack its parent allowed. Only granting requests the model already rated as plausible brought that down to 13% with Qwen3-8B, while 97% of normal tasks still finished.
- Mid-size LLMs (Qwen3 4B to 32B) picked the tightest permission sets.
- Smaller yes/no scoring models were much faster, but granted too much out of the box.
- Against CAPMAS ([Veski, Guerraoui, Froelicher, 2026](https://arxiv.org/abs/2609.06500)), a recent system for the same problem, 13% of attacks got through with mbla versus 69% with CAPMAS, and 97% of normal tasks finished versus 51%. CAPMAS decides faster.

More detail is in `report/` and `research/findings.md`.

## Reproducing

Everything runs from `bench/`; its README lists the steps in order. The raw model outputs aren't checked in because of their size.
