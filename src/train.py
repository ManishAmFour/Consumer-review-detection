"""
train.py
--------
Main training entrypoint.

Usage:
    python src/train.py --config configs/config.yaml --seed 42 --model_type gated
    python src/train.py --config configs/config.yaml --seed 42 --model_type gated_finetuned
    python src/train.py --config configs/config.yaml --seed 42 --model_type text_only
    python src/train.py --config configs/config.yaml --seed 42 --model_type image_only
    python src/train.py --config configs/config.yaml --seed 42 --model_type concat

Model selection uses VALIDATION F1 only (early stopping + checkpointing).
The test set is never touched by this script -- see evaluate.py for the
single, final test-set pass.
"""
from __future__ import annotations

import argparse
import copy
import os
import time
from typing import Dict, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

from dataset import AiGenFoodReviewDataset, build_dataloader, build_image_transform
from metrics import compute_metrics
from models import build_model
from tokenizer import Tokenizer
from utils import (
    Timer,
    count_parameters,
    detect_environment,
    get_logger,
    load_config,
    save_json,
    set_seed,
)


def _require_columns_configured(cfg: dict) -> None:
    cols = cfg["data"]["columns"]
    required = ["id_col", "text_col", "label_col"]
    if cfg["model"]["fusion"]["type"] != "text_only":
        required.append("image_col")
    missing = [c for c in required if cols.get(c) is None]
    if missing:
        raise ValueError(
            f"configs/config.yaml is missing data.columns entries: {missing}. "
            f"Run dataset_audit.py, confirm the real column names, and fill them in "
            f"before training."
        )


def build_datasets(cfg: dict, tokenizer: Tokenizer, modality: str):
    cols = cfg["data"]["columns"]
    image_dir = cfg["data"]["image_dir"]

    train_df = pd.read_csv(cfg["data"]["train_csv"])
    val_df = pd.read_csv(cfg["data"]["val_csv"])
    test_df = pd.read_csv(cfg["data"]["test_csv"])

    common_kwargs = dict(
        image_dir=image_dir,
        id_col=cols["id_col"],
        text_col=cols["text_col"],
        image_col=cols.get("image_col"),
        label_col=cols["label_col"],
        tokenizer=tokenizer,
        modality=modality,
    )

    train_ds = AiGenFoodReviewDataset(
        train_df, image_transform=build_image_transform(cfg["image"]["resize"], train=True), **common_kwargs
    )
    val_ds = AiGenFoodReviewDataset(
        val_df, image_transform=build_image_transform(cfg["image"]["resize"], train=False), **common_kwargs
    )
    test_ds = AiGenFoodReviewDataset(
        test_df, image_transform=build_image_transform(cfg["image"]["resize"], train=False), **common_kwargs
    )
    return train_ds, val_ds, test_ds


def build_optimizer(model: nn.Module, cfg: dict, model_type: str):
    tcfg = cfg["train"]
    lr_new = float(tcfg["lr_new_layers"])
    lr_ft = float(tcfg["lr_finetune_layers"])
    wd = float(tcfg["weight_decay"])

    param_groups = []
    if hasattr(model, "image_encoder") and model_type == "gated_finetuned":
        param_groups.extend(model.image_encoder.finetune_parameter_groups(lr_new, lr_ft))
        other_params = [p for n, p in model.named_parameters() if not n.startswith("image_encoder.") and p.requires_grad]
        param_groups.append({"params": other_params, "lr": lr_new})
    else:
        param_groups.append({"params": [p for p in model.parameters() if p.requires_grad], "lr": lr_new})

    return AdamW(param_groups, weight_decay=wd)


def run_epoch(
    model: nn.Module,
    loader,
    device: str,
    criterion,
    optimizer=None,
    scaler=None,
    grad_clip: float = 5.0,
) -> Dict:
    is_train = optimizer is not None
    model.train() if is_train else model.eval()

    all_probs, all_labels = [], []
    total_loss = 0.0
    n_batches = 0

    for batch in loader:
        labels = batch["label"].to(device, non_blocking=True)
        inputs = {k: v.to(device, non_blocking=True) for k, v in batch.items() if k in ("text_ids", "text_mask", "image")}

        with torch.set_grad_enabled(is_train):
            if scaler is not None and is_train:
                with torch.cuda.amp.autocast():
                    out = model(inputs)
                    loss = criterion(out["logit"], labels)
                optimizer.zero_grad()
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                out = model(inputs)
                loss = criterion(out["logit"], labels)
                if is_train:
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                    optimizer.step()

        probs = torch.sigmoid(out["logit"]).detach().cpu().numpy()
        all_probs.append(probs)
        all_labels.append(labels.detach().cpu().numpy())
        total_loss += loss.item()
        n_batches += 1

    y_prob = np.concatenate(all_probs)
    y_true = np.concatenate(all_labels)
    metrics = compute_metrics(y_true, y_prob, threshold=0.5)
    metrics["loss"] = total_loss / max(n_batches, 1)
    return metrics


def train_one_run(cfg: dict, seed: int, model_type: str, logger) -> Dict:
    set_seed(seed)
    env = detect_environment(print_report=True)
    device = env.device

    _require_columns_configured(cfg)
    modality = "text" if model_type == "text_only" else ("image" if model_type == "image_only" else "both")

    # ---- tokenizer: fit ONLY on training text ----
    cols = cfg["data"]["columns"]
    train_df = pd.read_csv(cfg["data"]["train_csv"])
    tokenizer = Tokenizer(
        max_seq_len=cfg["text"]["max_seq_len"],
        lowercase=cfg["text"]["lowercase"],
        min_token_freq=cfg["text"]["min_token_freq"],
        vocab_size_cap=cfg["text"]["vocab_size_cap"],
    )
    tokenizer.fit(train_df[cols["text_col"]].astype(str).tolist())
    os.makedirs(os.path.dirname(cfg["paths"]["vocab_path"]), exist_ok=True)
    tokenizer.save(cfg["paths"]["vocab_path"])
    logger.info(f"Tokenizer fit on TRAIN ONLY. vocab_size={tokenizer.vocab_size}")

    train_ds, val_ds, test_ds = build_datasets(cfg, tokenizer, modality)
    logger.info(
        f"Dataset sizes -> train: {len(train_ds)} (missing_images={train_ds.n_missing_images}), "
        f"val: {len(val_ds)} (missing_images={val_ds.n_missing_images}), "
        f"test: {len(test_ds)} (missing_images={test_ds.n_missing_images})"
    )

    tcfg = cfg["train"]
    train_loader = build_dataloader(
        train_ds, tcfg["batch_size"], shuffle=True, num_workers=tcfg["num_workers"],
        pin_memory=tcfg["pin_memory"], persistent_workers=tcfg["persistent_workers"], prefetch_factor=tcfg["prefetch_factor"],
    )
    val_loader = build_dataloader(
        val_ds, tcfg["batch_size"], shuffle=False, num_workers=tcfg["num_workers"],
        pin_memory=tcfg["pin_memory"], persistent_workers=tcfg["persistent_workers"], prefetch_factor=tcfg["prefetch_factor"],
    )

    # ---- configure model type / backbone freezing ----
    cfg = copy.deepcopy(cfg)
    if model_type == "gated_finetuned":
        cfg["model"]["image"]["unfreeze_last_block"] = True
        cfg["model"]["image"]["freeze_backbone"] = True  # still frozen except layer4
    elif model_type in ("gated", "concat", "image_only"):
        cfg["model"]["image"]["unfreeze_last_block"] = False
        cfg["model"]["image"]["freeze_backbone"] = True

    model = build_model(model_type, tokenizer.vocab_size, cfg).to(device)
    param_counts = count_parameters(model)
    logger.info(f"Parameter counts for {model_type}: {param_counts}")

    optimizer = build_optimizer(model, cfg, model_type)
    scheduler = ReduceLROnPlateau(
        optimizer, mode="max", factor=tcfg["lr_scheduler_factor"], patience=tcfg["lr_scheduler_patience"]
    )
    criterion = nn.BCEWithLogitsLoss()
    scaler = torch.cuda.amp.GradScaler() if (device == "cuda" and tcfg["mixed_precision"]) else None

    best_val_f1 = -1.0
    best_state = None
    epochs_no_improve = 0
    history = {"train_loss": [], "val_loss": [], "train_f1": [], "val_f1": []}

    ckpt_dir = cfg["paths"]["checkpoints_dir"]
    os.makedirs(ckpt_dir, exist_ok=True)
    ckpt_path = os.path.join(ckpt_dir, f"{model_type}_seed{seed}_best.pt")

    total_train_time = 0.0
    epoch_times = []

    for epoch in range(tcfg["max_epochs"]):
        with Timer() as t:
            train_metrics = run_epoch(model, train_loader, device, criterion, optimizer, scaler, tcfg["grad_clip_norm"])
        epoch_times.append(t.elapsed)
        total_train_time += t.elapsed

        val_metrics = run_epoch(model, val_loader, device, criterion, optimizer=None)
        scheduler.step(val_metrics["f1"])

        history["train_loss"].append(train_metrics["loss"])
        history["val_loss"].append(val_metrics["loss"])
        history["train_f1"].append(train_metrics["f1"])
        history["val_f1"].append(val_metrics["f1"])

        logger.info(
            f"[{model_type} seed={seed}] epoch {epoch+1}/{tcfg['max_epochs']} "
            f"train_loss={train_metrics['loss']:.4f} val_loss={val_metrics['loss']:.4f} "
            f"train_f1={train_metrics['f1']:.4f} val_f1={val_metrics['f1']:.4f} "
            f"epoch_time={t.elapsed:.1f}s"
        )

        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            best_state = copy.deepcopy(model.state_dict())
            epochs_no_improve = 0
            torch.save(
                {"model_state": best_state, "cfg": cfg, "model_type": model_type, "seed": seed, "vocab_size": tokenizer.vocab_size},
                ckpt_path,
            )
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= tcfg["early_stopping_patience"]:
                logger.info(f"Early stopping at epoch {epoch+1} (best_val_f1={best_val_f1:.4f})")
                break

    result = {
        "model_type": model_type,
        "seed": seed,
        "best_val_f1": best_val_f1,
        "n_epochs_trained": len(history["train_loss"]),
        "total_train_time_sec": total_train_time,
        "mean_epoch_time_sec": float(np.mean(epoch_times)) if epoch_times else None,
        "checkpoint_path": ckpt_path,
        "param_counts": param_counts,
        "history": history,
        "device": device,
        "gpu_name": env.gpu_name,
    }
    save_json(result, os.path.join(cfg["paths"]["results_dir"], f"train_history_{model_type}_seed{seed}.json"))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--model_type", type=str, required=True,
        choices=["text_only", "image_only", "concat", "gated", "gated_finetuned"],
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    logger = get_logger(f"train_{args.model_type}_seed{args.seed}", cfg["paths"]["logs_dir"])
    result = train_one_run(cfg, args.seed, args.model_type, logger)
    logger.info(f"DONE. best_val_f1={result['best_val_f1']:.4f} checkpoint={result['checkpoint_path']}")
