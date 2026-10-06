import argparse
import os
import re
import signal
import subprocess
import threading
import time
from pathlib import Path

import requests

from mbla_bench import data, run

SERVE_BIN = Path(".venv-serve/bin").resolve()
LOG_DIR = Path("results/logs")
HEALTH_TIMEOUT_SECONDS = 1800
IDLE_MEMORY_MIB = 2048
STARTUP_ATTEMPTS = 3
SHARED_FRACTION = 0.55
SHARED_MARGIN_MIB = 1024
SHARED_MODE = False
SHARED_HARDWARE = "shared GPU (other users' jobs present): latency not used, see e5"


def serving_environment(gpu_ids):
    environment = dict(os.environ)
    environment["PATH"] = f"{SERVE_BIN}:{environment['PATH']}"
    environment["CUDA_VISIBLE_DEVICES"] = ",".join(gpu_ids)
    environment.setdefault("HF_HOME", "/scratch/jbcall/huggingface")
    environment.setdefault("XDG_CACHE_HOME", "/scratch/jbcall/.cache")
    environment.setdefault("TMPDIR", "/scratch/jbcall/tmp")
    return environment


def wait_until_healthy(url, process):
    deadline = time.time() + HEALTH_TIMEOUT_SECONDS
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited with code {process.returncode} before {url} was healthy")
        try:
            if requests.get(url, timeout=5).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(5)
    raise RuntimeError(f"{url} not healthy after {HEALTH_TIMEOUT_SECONDS}s")


def gpu_memory_used_mib(gpu_id):
    query = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-i", gpu_id]
    return int(subprocess.run(query, capture_output=True, text=True, check=True).stdout.strip())


def gpu_memory_mib(gpu_id, field):
    query = ["nvidia-smi", f"--query-gpu={field}", "--format=csv,noheader,nounits", "-i", gpu_id]
    return int(subprocess.run(query, capture_output=True, text=True, check=True).stdout.strip())


def wait_until_idle(gpu_ids):
    while any(gpu_memory_used_mib(gpu_id) > IDLE_MEMORY_MIB for gpu_id in gpu_ids):
        time.sleep(15)


def gpu_has_room(gpu_id, fraction):
    return gpu_memory_mib(gpu_id, "memory.free") >= fraction * gpu_memory_mib(gpu_id, "memory.total") + SHARED_MARGIN_MIB


def has_room_now(gpu_ids, fraction):
    return all(gpu_has_room(gpu_id, fraction) for gpu_id in gpu_ids)


def wait_until_room(gpu_ids, fraction):
    while not has_room_now(gpu_ids, fraction):
        time.sleep(15)


def shared_command(command, fraction):
    return re.sub(r"--gpu-memory-utilization [0-9.]+", f"--gpu-memory-utilization {fraction}", command)


def start_servers(method, gpu_ids, log, processes):
    fraction = method.get("shared_fraction", SHARED_FRACTION)
    if SHARED_MODE:
        wait_until_room(gpu_ids, fraction)
    else:
        wait_until_idle(gpu_ids)
    for step in method["serve"]:
        command = shared_command(step["command"], fraction) if SHARED_MODE else step["command"]
        process = subprocess.Popen(
            command, shell=True, env=serving_environment(gpu_ids), stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        processes.append(process)
        wait_until_healthy(step["health"], process)


def stop_servers(processes):
    for process in reversed(processes):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    for process in processes:
        try:
            process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)


def runs_for(method_name, experiments, settings, models):
    planned = []
    for experiment_name in experiments:
        if method_name in settings["experiments"][experiment_name]["methods"]:
            planned += [(experiment_name, run_plan) for run_plan in run.planned_runs(settings, models, experiment_name, [method_name])]
    return planned


def execute_runs(planned):
    for experiment_name, run_plan in planned:
        run.execute(experiment_name, [run_plan], dry_run=False)


def evaluate_method(method_name, method, gpu_ids, experiments, settings, models):
    planned = [(name, plan) for name, plan in runs_for(method_name, experiments, settings, models) if not run.already_complete(*plan)]
    if not planned:
        return
    if "serve" not in method:
        execute_runs(planned)
        return
    with open(LOG_DIR / f"{method_name}.log", "a") as log:
        processes = start_with_retries(method_name, method, gpu_ids, log)
        try:
            execute_runs(planned)
        finally:
            stop_servers(processes)
    print(f"[{method_name}] done", flush=True)


def start_with_retries(method_name, method, gpu_ids, log):
    for attempt in range(1, STARTUP_ATTEMPTS + 1):
        print(f"[{method_name}] starting on gpu {','.join(gpu_ids)} (attempt {attempt})", flush=True)
        processes = []
        try:
            start_servers(method, gpu_ids, log, processes)
            return processes
        except RuntimeError:
            stop_servers(processes)
            if attempt == STARTUP_ATTEMPTS:
                raise
    return []


class GpuPool:
    def __init__(self, gpu_ids):
        self.free = list(gpu_ids)
        self.condition = threading.Condition()

    def acquire(self, count):
        with self.condition:
            self.condition.wait_for(lambda: len(self.free) >= count)
            taken, self.free = self.free[:count], self.free[count:]
            return taken

    def release(self, gpu_ids):
        with self.condition:
            self.free += gpu_ids
            self.condition.notify_all()


def gpus_with_room(pool, method):
    while True:
        gpu_ids = pool.acquire(method.get("gpus", 0))
        if not SHARED_MODE or has_room_now(gpu_ids, method.get("shared_fraction", SHARED_FRACTION)):
            return gpu_ids
        pool.release(gpu_ids)
        time.sleep(60)


def worker(method_name, method, pool, experiments, settings, models, failures):
    gpu_ids = gpus_with_room(pool, method) if "serve" in method else []
    try:
        evaluate_method(method_name, method, gpu_ids, experiments, settings, models)
    except (RuntimeError, OSError, subprocess.CalledProcessError, requests.RequestException) as error:
        failures.append(f"{method_name}: {error}")
        print(f"[{method_name}] FAILED: {error}", flush=True)
    finally:
        pool.release(gpu_ids)


def scheduling_order(method_names, models):
    if SHARED_MODE:
        return sorted(method_names, key=lambda name: models["methods"][name].get("shared_fraction", SHARED_FRACTION))
    return sorted(method_names, key=lambda name: -models["methods"][name].get("gpus", 0))


def main():
    parser = argparse.ArgumentParser(description="serve each model alone on its own gpu(s), run its experiments, stop it")
    parser.add_argument("--experiments", required=True, help="comma-separated, e.g. dev or e1,e3,e4")
    parser.add_argument("--methods", default="", help="comma-separated subset; default: every method in those experiments")
    parser.add_argument("--gpus", default="0,1,2,3")
    parser.add_argument(
        "--shared",
        action="store_true",
        help="share GPUs with other jobs: wait for free memory, smaller memory fraction, latency labelled unusable",
    )
    arguments = parser.parse_args()
    settings, models = data.load_yaml(run.EXPERIMENTS), data.load_yaml(run.MODELS)
    if arguments.shared:
        global SHARED_MODE
        SHARED_MODE = True
        settings["hardware"] = SHARED_HARDWARE
    experiments = arguments.experiments.split(",")
    listed = {name for experiment in experiments for name in settings["experiments"][experiment]["methods"]}
    method_names = [name for name in arguments.methods.split(",") if name] or sorted(listed)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    pool, failures, threads = GpuPool(arguments.gpus.split(",")), [], []
    for method_name in scheduling_order(method_names, models):
        thread = threading.Thread(
            target=worker, args=(method_name, models["methods"][method_name], pool, experiments, settings, models, failures)
        )
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    if failures:
        raise SystemExit("failed: " + "; ".join(failures))


if __name__ == "__main__":
    main()
