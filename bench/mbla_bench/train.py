"""fine-tunes helpers on the synthetic set (methodology §7): deployed prompt and schema, synthetic train and validation only."""
import argparse
import json
import math
import random
import re
from pathlib import Path

from mbla_bench import answer, data

GO_PROMPT = Path("../mbla/remote.go")
WARMUP = 0.03
EPOCHS = 2
LEARNING_RATES = (5e-6, 1e-5, 2e-5)
SEEDS = (0, 1, 2)
GRADED = {"required": 1.0, "plausible": 0.5, "unneeded": 0.0}


def instructions():
    return re.search(r"const chatInstructions = `(.*?)`", GO_PROMPT.read_text(), re.S).group(1)


def describe(request):
    return f"task: {request['text']}\n" + "".join(f"manifest: {permission}\n" for permission in request.get("manifest", []))


def chat_prompt(request, permissions):
    return f"Delegated request:\n{describe(request)}\nCandidate permissions:\n" + "".join(f"{index}. {permission}\n" for index, permission in enumerate(permissions))


def graded(item):
    required, plausible = answer.tiers(item)
    tier = {str(atom): "plausible" for atom in plausible}
    tier.update({str(atom): "required" for atom in required})
    return {str(atom): tier.get(str(atom), "unneeded") for atom in answer.candidates(item)}


def selection(item, rng):
    """the task with candidates in a fresh order, and the answer in the deployed output format."""
    tiers = list(graded(item).items())
    rng.shuffle(tiers)
    permissions = [permission for permission, _ in tiers]
    chosen = {name: [index for index, (_, tier) in enumerate(tiers) if tier == name] for name in ("required", "plausible")}
    return chat_prompt(item["request"], permissions), json.dumps(chosen, separators=(",", ":"))


def pairs(items):
    return [(describe(item["request"]), permission, GRADED[tier]) for item in items for permission, tier in graded(item).items()]


def chunks(batch, size):
    return [batch[start : start + size] for start in range(0, len(batch), size)]


def schedule(step, total):
    warm = max(int(total * WARMUP), 1)
    return (step + 1) / warm if step < warm else 0.5 * (1 + math.cos(math.pi * (step - warm) / max(total - warm, 1)))


class Generative:
    """learns the {required, plausible} answer; only the answer's tokens carry loss."""

    batch_size = 8
    chunk_size = 2

    def __init__(self, tokenizer, device):
        self.tokenizer, self.device = tokenizer, device
        self.system = instructions()

    def batches(self, items, rng):
        order = rng.sample(items, len(items))
        return [order[start : start + self.batch_size] for start in range(0, len(order), self.batch_size)]

    def encode(self, item, rng):
        user, target = selection(item, rng)
        messages = [{"role": "system", "content": self.system}, {"role": "user", "content": user}]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        start = self.tokenizer(prompt, add_special_tokens=False)["input_ids"]
        answer_ids = self.tokenizer(target + "<|im_end|>", add_special_tokens=False)["input_ids"]
        return start + answer_ids, [-100] * len(start) + answer_ids

    def loss(self, model, batch, rng):
        import torch

        encoded = [self.encode(item, rng) for item in batch]
        longest = max(len(ids) for ids, _ in encoded)
        pad = self.tokenizer.pad_token_id
        ids = torch.tensor([[pad] * (longest - len(row)) + row for row, _ in encoded], device=self.device)
        labels = torch.tensor([[-100] * (longest - len(row)) + row for _, row in encoded], device=self.device)
        mask = torch.tensor([[0] * (longest - len(row)) + [1] * len(row) for row, _ in encoded], device=self.device)
        keep = longest - (labels != -100).int().argmax(dim=1).min().item() + 1
        positions = (mask.cumsum(dim=1) - 1).clamp(min=0)
        logits = model(input_ids=ids, attention_mask=mask, position_ids=positions, logits_to_keep=keep).logits[:, :-1]
        return torch.nn.functional.cross_entropy(logits.reshape(-1, logits.size(-1)), moved(labels[:, 1 - keep:].reshape(-1), logits.device), ignore_index=-100)


class Scorer:
    """learns graded yes-probabilities, as the deployed reranker reads them."""

    batch_size = 32
    chunk_size = 8

    def __init__(self, tokenizer, device):
        self.tokenizer, self.device = tokenizer, device
        self.yes, self.no = tokenizer.convert_tokens_to_ids("yes"), tokenizer.convert_tokens_to_ids("no")

    def batches(self, items, rng):
        order = rng.sample(pairs(items), len(pairs(items)))
        return [order[start : start + self.batch_size] for start in range(0, len(order), self.batch_size)]

    def loss(self, model, batch, rng):
        import torch

        from serve.decision_server import RERANKER_INSTRUCTION, RERANKER_PREFIX as prefix, RERANKER_SUFFIX as suffix

        texts = [f"{prefix}<Instruct>: {RERANKER_INSTRUCTION}\n<Query>: {state}\n<Document>: {permission}{suffix}" for state, permission, _ in batch]
        encoded = self.tokenizer(texts, padding=True, truncation=True, max_length=8192, return_tensors="pt").to(self.device)
        logits = model(**encoded, logits_to_keep=1).logits[:, -1, :]
        yes_no = torch.stack([logits[:, self.no], logits[:, self.yes]], dim=1).float().log_softmax(dim=1)
        targets = torch.tensor([grade for _, _, grade in batch], device=logits.device)
        return -(targets * yes_no[:, 1] + (1 - targets) * yes_no[:, 0]).mean()


def moved(tensor, device):
    """direct copies from one gpu to another come back wrong on this machine (D-55), so they go through the cpu."""
    import torch

    return tensor if tensor.device == torch.device(device) else tensor.cpu().to(device)


def copy_through_cpu():
    import accelerate.hooks
    import torch
    from accelerate.utils import recursively_apply

    def send(data, device, non_blocking=False, skip_keys=None):
        return recursively_apply(lambda tensor: moved(tensor, device), data, test_type=torch.is_tensor)

    accelerate.hooks.send_to_device = send


def clip_gradients(model, limit):
    import torch

    gradients = [parameter.grad for parameter in model.parameters() if parameter.grad is not None]
    total = torch.stack([gradient.float().norm().cpu() for gradient in gradients]).norm()
    scale = (limit / (total + 1e-6)).clamp(max=1.0).item()
    for gradient in gradients:
        gradient.mul_(scale)
    return total.item()


def load(model_id, revision, qlora):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    copy_through_cpu()
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, padding_side="left" if "Reranker" in model_id else "right")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    if not qlora:
        return tokenizer, AutoModelForCausalLM.from_pretrained(model_id, revision=revision, dtype=torch.bfloat16, device_map="auto")
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import BitsAndBytesConfig

    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, quantization_config=quantization, device_map="auto")
    return tokenizer, get_peft_model(prepare_model_for_kbit_training(model), LoraConfig(r=16, lora_alpha=32, target_modules="all-linear", task_type="CAUSAL_LM"))


def validate(model, task, items):
    import torch

    rng = random.Random(0)
    model.eval()
    losses = []
    with torch.no_grad():
        for batch in task.batches(items, rng):
            losses += [(task.loss(model, chunk, rng).item(), len(chunk)) for chunk in chunks(batch, task.chunk_size)]
    model.train()
    return sum(value * size for value, size in losses) / sum(size for _, size in losses)


def fit(arguments):
    import torch

    random.seed(arguments.seed)
    torch.manual_seed(arguments.seed)
    tokenizer, model = load(arguments.model, arguments.revision, arguments.qlora)
    task = (Scorer if "Reranker" in arguments.model else Generative)(tokenizer, "cuda")
    train = data.read_jsonl(arguments.train)[: arguments.limit]
    validation = data.read_jsonl(arguments.validation)[: arguments.limit]
    rng = random.Random(arguments.seed)
    total = EPOCHS * len(task.batches(train, rng))
    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    model.train()
    optimizer = torch.optim.AdamW([parameter for parameter in model.parameters() if parameter.requires_grad], lr=arguments.learning_rate)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: schedule(step, total))
    out = Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    history, best, step = [], float("inf"), 0
    for epoch in range(EPOCHS):
        for batch in task.batches(train, rng):
            for chunk in chunks(batch, task.chunk_size):
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    loss = task.loss(model, chunk, rng) * len(chunk) / len(batch)
                if not math.isfinite(loss.item()):
                    raise SystemExit(f"loss is not finite at step {step}")
                loss.backward()
            clip_gradients(model, 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            step += 1
        score = validate(model, task, validation)
        history.append({"epoch": epoch + 1, "steps": step, "validation_loss": score})
        print(history[-1], flush=True)
        if score < best:
            best = score
            model.save_pretrained(out)
            tokenizer.save_pretrained(out)
    (out / "history.json").write_text(json.dumps({"settings": vars(arguments), "history": history}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--learning-rate", type=float, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--train", default="data/tasks/synth_train.jsonl")
    parser.add_argument("--validation", default="data/tasks/synth_validation.jsonl")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--qlora", action="store_true")
    fit(parser.parse_args())


if __name__ == "__main__":
    main()
