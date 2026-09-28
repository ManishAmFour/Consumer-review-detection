"""
compute_cost.py
----------------
PHASE 15 / spec section 13. Measures REAL computational cost for each of
the five models:

  - trainable / frozen / total parameter counts (torch, exact, not estimated)
  - peak GPU memory during a real forward+backward pass (CUDA only; reports
    "N/A (no CUDA device)" honestly on CPU rather than fabricating a number)
  - training time per epoch (pulled from the actual train_history_*.json
    written by train.py -- this script does NOT re-estimate it)
  - inference latency (ms/sample) and throughput (samples/sec), measured
    with real repeated forward passes at batch_size=1 on the ACTUAL trained
    checkpoint's architecture

Usage:
    python src/compute_cost.py --config configs/config.yaml \
        --checkpoints checkpoints/text_only_seed42_best.pt checkpoints/gated_seed42_best.pt ...
"""
from __future__ import annotations

import argparse
import time
from typing import Dict, List

import numpy as np
import pandas as pd
import torch

from models import build_model
from utils import count_parameters, detect_environment, load_config, save_json


def _dummy_batch(model_type: str, cfg: dict, vocab_size: int, batch_size: int, device: str) -> Dict:
    batch = {}
    if model_type != "image_only":
        max_len = cfg["text"]["max_seq_len"]
        batch["text_ids"] = torch.randint(0, max(vocab_size, 2), (batch_size, max_len), device=device)
        batch["text_mask"] = torch.ones(batch_size, max_len, dtype=torch.bool, device=device)
    if model_type != "text_only":
        resize = cfg["image"]["resize"]
        batch["image"] = torch.randn(batch_size, 3, resize, resize, device=device)
    return batch


def measure_inference_latency(model, model_type, cfg, vocab_size, device, n_runs: int = 200) -> Dict:
    model.eval()
    batch = _dummy_batch(model_type, cfg, vocab_size, batch_size=1, device=device)

    # warmup (excluded from timing -- first CUDA call includes kernel compile/alloc overhead)
    with torch.no_grad():
        for _ in range(10):
            model(batch)
    if device == "cuda":
        torch.cuda.synchronize()

    times = []
    with torch.no_grad():
        for _ in range(n_runs):
            t0 = time.perf_counter()
            model(batch)
            if device == "cuda":
                torch.cuda.synchronize()
            times.append(time.perf_counter() - t0)

    times = np.array(times)
    return {
        "n_runs": n_runs,
        "batch_size": 1,
        "mean_latency_ms": float(times.mean() * 1000),
        "std_latency_ms": float(times.std() * 1000),
        "p50_latency_ms": float(np.percentile(times, 50) * 1000),
        "p95_latency_ms": float(np.percentile(times, 95) * 1000),
        "throughput_samples_per_sec": float(1.0 / times.mean()),
    }


def measure_gpu_memory(model, model_type, cfg, vocab_size, device) -> Dict:
    if device != "cuda":
        return {"peak_gpu_memory_mb": "N/A (no CUDA device available in this run)"}

    torch.cuda.reset_peak_memory_stats()
    model.train()
    batch = _dummy_batch(model_type, cfg, vocab_size, batch_size=cfg["train"]["batch_size"], device=device)
    labels = torch.randint(0, 2, (cfg["train"]["batch_size"],), dtype=torch.float32, device=device)
    out = model(batch)
    loss = torch.nn.functional.binary_cross_entropy_with_logits(out["logit"], labels)
    loss.backward()
    torch.cuda.synchronize()
    peak_mb = torch.cuda.max_memory_allocated() / (1024 ** 2)
    return {"peak_gpu_memory_mb": float(peak_mb), "batch_size_used": cfg["train"]["batch_size"]}


def analyze_checkpoint(checkpoint_path: str, cfg: dict, device: str) -> Dict:
    ckpt = torch.load(checkpoint_path, map_location=device)
    model_type = ckpt["model_type"]
    saved_cfg = ckpt["cfg"]
    vocab_size = ckpt["vocab_size"]

    model = build_model(model_type, vocab_size, saved_cfg).to(device)
    model.load_state_dict(ckpt["model_state"])

    params = count_parameters(model)
    latency = measure_inference_latency(model, model_type, saved_cfg, vocab_size, device,
                                         n_runs=cfg["compute_analysis"]["inference_latency_num_runs"])
    gpu_mem = measure_gpu_memory(model, model_type, saved_cfg, vocab_size, device)

    # training time comes from the actual saved training history, never re-estimated here
    try:
        from utils import load_json
        hist = load_json(f"{cfg['paths']['results_dir']}/train_history_{model_type}_seed{ckpt['seed']}.json")
        train_time = {
            "total_train_time_sec": hist["total_train_time_sec"],
            "mean_epoch_time_sec": hist["mean_epoch_time_sec"],
            "n_epochs_trained": hist["n_epochs_trained"],
        }
    except FileNotFoundError:
        train_time = {"status": "train_history JSON not found -- run train.py first for this checkpoint"}

    return {
        "model_type": model_type,
        "checkpoint": checkpoint_path,
        "parameters": params,
        "training_time": train_time,
        "inference_latency": latency,
        "gpu_memory": gpu_mem,
    }


def main(config_path: str, checkpoints: List[str]):
    cfg = load_config(config_path)
    env = detect_environment(print_report=True)
    device = env.device

    rows = []
    for ckpt_path in checkpoints:
        print(f"Analyzing {ckpt_path} ...")
        result = analyze_checkpoint(ckpt_path, cfg, device)
        rows.append(
            {
                "model_type": result["model_type"],
                "trainable_params": result["parameters"]["trainable_params"],
                "frozen_params": result["parameters"]["frozen_params"],
                "total_params": result["parameters"]["total_params"],
                "peak_gpu_memory_mb": result["gpu_memory"].get("peak_gpu_memory_mb"),
                "total_train_time_sec": result["training_time"].get("total_train_time_sec"),
                "mean_epoch_time_sec": result["training_time"].get("mean_epoch_time_sec"),
                "inference_latency_ms": result["inference_latency"]["mean_latency_ms"],
                "throughput_samples_per_sec": result["inference_latency"]["throughput_samples_per_sec"],
            }
        )

    df = pd.DataFrame(rows)
    out_csv = f"{cfg['paths']['results_dir']}/computational_cost.csv"
    df.to_csv(out_csv, index=False)
    save_json(rows, f"{cfg['paths']['results_dir']}/computational_cost.json")
    print(f"Computational cost table written to {out_csv}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--checkpoints", type=str, nargs="+", required=True)
    args = parser.parse_args()
    main(args.config, args.checkpoints)
