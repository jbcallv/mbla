"""retrain CAPMAS on our synthetic train split with its own train.py and paper settings (D-20, §7). only the base
encoder, the seed and the run name change. checkpoint chosen by their own rule on our synthetic validation split.
encoders load in float32, as bge-large does by default: their trainer's fp16 gradient scaler needs float32 weights,
and Qwen3-Embedding otherwise loads in bfloat16."""

import argparse
import os
import sys
from pathlib import Path

SOURCE = Path("data/external/capmas-src/semantic_scoping").resolve()
ENCODERS = {
    "bge-large": "BAAI/bge-large-en-v1.5",
    "qwen3-embedding-0.6b": "Qwen/Qwen3-Embedding-0.6B",
}


def config(encoder, seed):
    return {
        "experiment_name": f"{encoder}-s{seed}",
        "dataset": "MBLA",
        "strategy": "synth",
        "model": {"architecture": "shared", "base_model": ENCODERS[encoder], "latent_dim": 512},
        "training": {"batch_size": 128, "grad_accum_steps": 1, "epochs": 15, "learning_rate": 2.0e-5, "patience": 3, "eval_k": 5, "max_length": 256},
    }


def main():
    parser = argparse.ArgumentParser(description="retrain CAPMAS with its own code")
    parser.add_argument("--encoder", choices=sorted(ENCODERS), required=True)
    parser.add_argument("--seed", type=int, required=True)
    arguments = parser.parse_args()
    os.chdir(SOURCE)
    sys.path.insert(0, str(SOURCE))
    import torch
    import train
    import transformers

    loader = transformers.AutoModel.from_pretrained
    transformers.AutoModel.from_pretrained = lambda *args, **kwargs: loader(*args, **{"dtype": torch.float32, **kwargs})
    original = train.set_seed
    train.set_seed = lambda _: original(arguments.seed)
    train.train_pipeline(config(arguments.encoder, arguments.seed))


if __name__ == "__main__":
    main()
