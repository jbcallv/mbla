"""trains every helper on two gpus: each learning rate on seed 0, then seeds 1 and 2 at the best one (§7)."""
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from mbla_bench.train import LEARNING_RATES, SEEDS

MODELS = ["Qwen/Qwen3-1.7B", "Qwen/Qwen3-Reranker-0.6B", "Qwen/Qwen3-4B", "Qwen/Qwen3-8B", "Qwen/Qwen3-Reranker-8B"]
HUB = Path("/scratch/jbcall/huggingface/hub")
OUT = Path("models")


def revision(model):
    return next((HUB / f"models--{model.replace('/', '--')}" / "snapshots").iterdir()).name


def run(model, rate, seed, gpu):
    out = OUT / model.split("/")[1] / f"lr{rate}-seed{seed}"
    if (out / "history.json").exists():
        return out
    environment = {**os.environ, "CUDA_VISIBLE_DEVICES": str(gpu), "HF_HOME": "/scratch/jbcall/huggingface", "PYTHONPATH": os.getcwd()}
    command = [sys.executable, "-m", "mbla_bench.train", "--model", model, "--revision", revision(model), "--learning-rate", str(rate), "--seed", str(seed), "--out", str(out)]
    print(gpu, "start", out, flush=True)
    subprocess.run(command, env=environment, check=True)
    return out


def best_loss(out):
    return min(entry["validation_loss"] for entry in json.loads((out / "history.json").read_text())["history"])


def train_model(model, gpu):
    first = {rate: best_loss(run(model, rate, SEEDS[0], gpu)) for rate in LEARNING_RATES}
    chosen = min(first, key=first.get)
    for seed in SEEDS[1:]:
        run(model, chosen, seed, gpu)
    (OUT / model.split("/")[1] / "selection.json").write_text(json.dumps({"seed_0_loss": first, "chosen": chosen}, indent=2) + "\n")
    print(gpu, "done", model, chosen, flush=True)


def worker(jobs, gpu):
    while True:
        try:
            model = jobs.get_nowait()
        except queue.Empty:
            return
        try:
            train_model(model, gpu)
        except subprocess.CalledProcessError as error:
            print(gpu, "failed", model, error, flush=True)


def main():
    jobs = queue.Queue()
    for model in MODELS:
        jobs.put(model)
    threads = [threading.Thread(target=worker, args=(jobs, gpu)) for gpu in sys.argv[1:]]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
