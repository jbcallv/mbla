import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import pairwise

QUESTION = "Is this permission required to complete the delegated task? Permission: "
RERANKER_INSTRUCTION = "Decide whether the delegated task in the Query needs the permission in the Document."
RERANKER_PREFIX = (
    "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. "
    'Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
)
RERANKER_CHUNK = 16
EMBEDDING_LATENT_DIM = 512
RERANKER_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


class Qwen3Reranker:
    def __init__(self, model_id, revision):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, padding_side="left")
        self.model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, dtype=torch.bfloat16).to("cuda").eval()
        self.yes_token = self.tokenizer.convert_tokens_to_ids("yes")
        self.no_token = self.tokenizer.convert_tokens_to_ids("no")

    def prompt(self, state, candidate):
        return f"{RERANKER_PREFIX}<Instruct>: {RERANKER_INSTRUCTION}\n<Query>: {state}\n<Document>: {candidate}{RERANKER_SUFFIX}"

    def score(self, state, candidates):
        prompts = [self.prompt(state, candidate) for candidate in candidates]
        scores = []
        for start in range(0, len(prompts), RERANKER_CHUNK):
            scores += self.score_chunk(prompts[start : start + RERANKER_CHUNK])
        return scores

    def score_chunk(self, prompts):
        batch = self.tokenizer(prompts, padding=True, truncation=True, max_length=8192, return_tensors="pt").to("cuda")
        with self.torch.no_grad():
            last_logits = self.model(**batch, logits_to_keep=1).logits[:, -1, :]
        yes_no = self.torch.stack([last_logits[:, self.no_token], last_logits[:, self.yes_token]], dim=1)
        return yes_no.float().log_softmax(dim=1)[:, 1].exp().tolist()


class Laya:
    def __init__(self, model_id, revision):
        import laya

        self.agent = laya.load(model_id, revision=revision)

    def score(self, state, candidates):
        questions = {f"c{index}": {"type": "noul", "instructions": QUESTION + candidate} for index, candidate in enumerate(candidates)}
        answers = self.agent.predict(state, questions)["answers"]
        return [float(answers[f"c{index}"]["noul"]) for index in range(len(candidates))]


def capmas_text(candidate):
    permission, _, meaning = candidate.partition(" (")
    service, operation, resource = (permission.split(":", 2) + ["", ""])[:3]
    scope = "" if resource in ("skill", "tool", "") else f" on '{resource}'"
    return f"Using service environment '{service}', execute capacity '{operation}'{scope} to: {meaning.rstrip(')') or operation}"


def elbow_selection(similarities, top_k, drop):
    ranked = sorted(range(len(similarities)), key=lambda index: -similarities[index])[:top_k]
    chosen = ranked[:1]
    for previous, current in pairwise(ranked):
        if similarities[previous] - similarities[current] > drop:
            break
        chosen.append(current)
    return [1.0 if index in chosen else 0.0 for index in range(len(similarities))]


class Embedding:
    def __init__(self, model_id, revision, checkpoint, selection, top_k, drop):
        import torch
        from torch import nn
        from transformers import AutoModel, AutoTokenizer

        self.torch, self.selection, self.top_k, self.drop = torch, selection, top_k, drop
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self.model = nn.Module()
        self.model.shared_encoder = AutoModel.from_pretrained(model_id, revision=revision)
        self.model.shared_proj = None
        if checkpoint:
            hidden = self.model.shared_encoder.config.hidden_size
            self.model.shared_proj = nn.Sequential(nn.Linear(hidden, hidden), nn.GELU(), nn.Linear(hidden, EMBEDDING_LATENT_DIM))
            self.model.logit_scale = nn.Parameter(torch.zeros([]))
            self.model.load_state_dict(torch.load(checkpoint, map_location="cpu"))
        self.model.to("cuda").eval()

    def encode(self, texts):
        batch = self.tokenizer(texts, padding=True, truncation=True, max_length=256, return_tensors="pt").to("cuda")
        with self.torch.no_grad():
            tokens = self.model.shared_encoder(**batch)[0]
            mask = batch["attention_mask"].unsqueeze(-1).float()
            pooled = (tokens * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            projected = self.model.shared_proj(pooled) if self.model.shared_proj is not None else pooled
            return self.torch.nn.functional.normalize(projected, p=2, dim=-1)

    def score(self, state, candidates):
        query = self.encode([state])
        similarities = (self.encode([capmas_text(candidate) for candidate in candidates]) @ query.T).squeeze(1).tolist()
        if self.selection == "elbow":
            return elbow_selection(similarities, self.top_k, self.drop)
        return similarities


def load_backend(arguments):
    if arguments.backend == "qwen3-reranker":
        return Qwen3Reranker(arguments.model, arguments.revision)
    if arguments.backend == "embedding":
        return Embedding(arguments.model, arguments.revision, arguments.checkpoint, arguments.selection, arguments.top_k, arguments.drop)
    return Laya(arguments.model, arguments.revision)


def handler_for(backend, model_label):
    class ScoreHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.reply(200, {"status": "ok"}) if self.path == "/health" else self.send_error(404)

        def do_POST(self):
            if self.path != "/score":
                self.send_error(404)
                return
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.reply(200, {"model": model_label, "scores": backend.score(request["state"], request["candidates"])})

        def reply(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    return ScoreHandler


def main():
    parser = argparse.ArgumentParser(description="serves a yes/no decision model behind the /score api the go Decision scorer calls")
    parser.add_argument("--backend", required=True, choices=["qwen3-reranker", "laya", "embedding"])
    parser.add_argument("--checkpoint", default=None, help="embedding backend: CAPMAS-trained weights (shared encoder + projection)")
    parser.add_argument(
        "--selection",
        default="scores",
        choices=["scores", "elbow"],
        help="embedding backend: raw cosine scores, or CAPMAS top-k + elbow drop",
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--drop", type=float, default=0.2)
    parser.add_argument("--model", default="")
    parser.add_argument("--revision", default=None)
    parser.add_argument("--port", type=int, required=True)
    arguments = parser.parse_args()
    model_label = f"{arguments.model or arguments.backend}@{arguments.revision or 'default'}"
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), handler_for(load_backend(arguments), model_label))
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
