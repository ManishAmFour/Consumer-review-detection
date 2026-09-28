"""
evaluate.py
-----------
Loads a trained checkpoint and produces the final, single-pass test
evaluation, following the spec's strict thresholding protocol:

  1. Run inference on VALIDATION -> select threshold maximizing val F1.
  2. FREEZE that threshold.
  3. Run inference on TEST exactly once using both:
       (a) the default 0.50 threshold
       (b) the frozen validation-selected threshold
  The test set is never used to choose anything.

Usage:
    python src/evaluate.py --config configs/config.yaml --checkpoint checkpoints/gated_seed42_best.pt
"""
from __future__ import annotations

import argparse
import os
from typing import Dict

import numpy as np
import pandas as pd
import torch

from dataset import AiGenFoodReviewDataset, build_dataloader, build_image_transform
from metrics import compute_metrics, select_threshold_on_validation
from models import build_model
from tokenizer import Tokenizer
from utils import detect_environment, load_config, save_json


@torch.no_grad()
def get_predictions(model, loader, device) -> Dict[str, np.ndarray]:
    model.eval()
    all_probs, all_labels, all_ids, all_gates = [], [], [], []
    for batch in loader:
        labels = batch["label"].to(device)
        inputs = {k: v.to(device) for k, v in batch.items() if k in ("text_ids", "text_mask", "image")}
        out = model(inputs)
        probs = torch.sigmoid(out["logit"]).cpu().numpy()
        all_probs.append(probs)
        all_labels.append(labels.cpu().numpy())
        all_ids.extend(batch["id"])
        if "gate" in out:
            all_gates.append(out["gate"].cpu().numpy())

    result = {
        "ids": np.array(all_ids),
        "y_true": np.concatenate(all_labels),
        "y_prob": np.concatenate(all_probs),
    }
    if all_gates:
        result["gate_mean_per_sample"] = np.concatenate(all_gates).mean(axis=1)
    return result


def evaluate_checkpoint(cfg: dict, checkpoint_path: str) -> Dict:
    env = detect_environment(print_report=True)
    device = env.device

    ckpt = torch.load(checkpoint_path, map_location=device)
    model_type = ckpt["model_type"]
    saved_cfg = ckpt["cfg"]
    vocab_size = ckpt["vocab_size"]

    tokenizer = Tokenizer.load(cfg["paths"]["vocab_path"])
    assert tokenizer.vocab_size == vocab_size, (
        f"Vocab size mismatch: checkpoint expects {vocab_size}, loaded tokenizer has "
        f"{tokenizer.vocab_size}. Make sure you're using the tokenizer saved alongside this run."
    )

    modality = "text" if model_type == "text_only" else ("image" if model_type == "image_only" else "both")
    cols = cfg["data"]["columns"]
    val_df = pd.read_csv(cfg["data"]["val_csv"])
    test_df = pd.read_csv(cfg["data"]["test_csv"])

    common_kwargs = dict(
        image_dir=cfg["data"]["image_dir"],
        id_col=cols["id_col"],
        text_col=cols["text_col"],
        image_col=cols.get("image_col"),
        label_col=cols["label_col"],
        tokenizer=tokenizer,
        modality=modality,
    )
    val_ds = AiGenFoodReviewDataset(val_df, image_transform=build_image_transform(cfg["image"]["resize"], train=False), **common_kwargs)
    test_ds = AiGenFoodReviewDataset(test_df, image_transform=build_image_transform(cfg["image"]["resize"], train=False), **common_kwargs)

    val_loader = build_dataloader(val_ds, cfg["train"]["batch_size"], shuffle=False, num_workers=2, pin_memory=(device == "cuda"))
    test_loader = build_dataloader(test_ds, cfg["train"]["batch_size"], shuffle=False, num_workers=2, pin_memory=(device == "cuda"))

    model = build_model(model_type, vocab_size, saved_cfg).to(device)
    model.load_state_dict(ckpt["model_state"])

    # ---- Step 1: validation predictions, threshold selection ----
    val_preds = get_predictions(model, val_loader, device)
    selected_threshold, val_best_score = select_threshold_on_validation(
        val_preds["y_true"], val_preds["y_prob"], metric=cfg["threshold"]["selection_metric"]
    )

    # ---- Step 2: FREEZE threshold, run test exactly once ----
    test_preds = get_predictions(model, test_loader, device)

    default_metrics = compute_metrics(test_preds["y_true"], test_preds["y_prob"], threshold=cfg["threshold"]["default"])
    frozen_metrics = compute_metrics(test_preds["y_true"], test_preds["y_prob"], threshold=selected_threshold)

    result = {
        "model_type": model_type,
        "checkpoint_path": checkpoint_path,
        "seed": ckpt.get("seed"),
        "validation_selected_threshold": selected_threshold,
        "validation_score_at_selected_threshold": val_best_score,
        "test_results_default_threshold_0.5": default_metrics,
        "test_results_validation_selected_threshold": frozen_metrics,
        "n_test_samples": int(len(test_preds["y_true"])),
    }

    # save raw predictions for downstream error analysis / statistical tests
    pred_df = pd.DataFrame(
        {
            "id": test_preds["ids"],
            "y_true": test_preds["y_true"],
            "y_prob": test_preds["y_prob"],
        }
    )
    if "gate_mean_per_sample" in test_preds:
        pred_df["gate_mean"] = test_preds["gate_mean_per_sample"]

    os.makedirs(cfg["paths"]["results_dir"], exist_ok=True)
    pred_path = os.path.join(cfg["paths"]["results_dir"], f"predictions_{model_type}_seed{ckpt.get('seed')}.csv")
    pred_df.to_csv(pred_path, index=False)
    result["predictions_csv"] = pred_path

    save_json(
        result,
        os.path.join(cfg["paths"]["results_dir"], f"eval_{model_type}_seed{ckpt.get('seed')}.json"),
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--checkpoint", type=str, required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    res = evaluate_checkpoint(cfg, args.checkpoint)
    print(res["test_results_default_threshold_0.5"])
    print(res["test_results_validation_selected_threshold"])
