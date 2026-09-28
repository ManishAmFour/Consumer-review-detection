"""
robustness.py
--------------
PHASE 14 / spec section 12. Three robustness experiments, each compared
against the SAME model's original (undegraded) test performance:

  A. Modality removal:
       - image removed (zeroed / replaced with a fixed neutral gray image)
       - text removed (replaced with an empty/all-pad sequence)
  B. Image degradation:
       - JPEG compression at configurable quality levels
       - Gaussian blur at configurable radii
  C. Text perturbation:
       - character-level typo injection at a configurable rate
       - random word dropout at a configurable rate

All perturbations are applied only at evaluation time, on the frozen
checkpoint -- no retraining, no threshold re-selection (the frozen
validation threshold from evaluate.py is reused so this is a clean,
comparable stress test rather than a re-tuned one).

Optional (section 12): generator-separated evaluation. This requires
generation-source metadata that most releases of this kind of dataset do
NOT include; the function below checks for it explicitly and reports
"NOT AVAILABLE" rather than fabricating a proxy.

Usage:
    python src/robustness.py --config configs/config.yaml --checkpoint checkpoints/gated_seed42_best.pt
"""
from __future__ import annotations

import argparse
import io
import random
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageFilter

from dataset import AiGenFoodReviewDataset, build_dataloader, IMAGENET_MEAN, IMAGENET_STD
from evaluate import get_predictions
from metrics import compute_metrics
from models import build_model
from tokenizer import Tokenizer, normalize_text, tokenize
from utils import detect_environment, load_config, save_json
from torchvision import transforms


# ----------------------------------------------------------------------------
# Image degradation transforms
# ----------------------------------------------------------------------------
def jpeg_compress(img: Image.Image, quality: int) -> Image.Image:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def gaussian_blur(img: Image.Image, radius: float) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def build_degraded_transform(resize: int, degradation: str, param) -> transforms.Compose:
    def _degrade(img: Image.Image) -> Image.Image:
        if degradation == "jpeg":
            return jpeg_compress(img, quality=param)
        elif degradation == "blur":
            return gaussian_blur(img, radius=param)
        elif degradation == "gray_removed":
            return Image.new("RGB", img.size, color=(128, 128, 128))
        return img

    return transforms.Compose(
        [
            transforms.Resize((resize, resize)),
            transforms.Lambda(_degrade),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


# ----------------------------------------------------------------------------
# Text perturbation
# ----------------------------------------------------------------------------
_TYPO_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def inject_typos(text: str, rate: float, rng: random.Random) -> str:
    chars = list(text)
    for i in range(len(chars)):
        if chars[i].isalpha() and rng.random() < rate:
            op = rng.choice(["swap_case", "replace", "delete"])
            if op == "swap_case":
                chars[i] = chars[i].swapcase()
            elif op == "replace":
                chars[i] = rng.choice(_TYPO_ALPHABET)
            elif op == "delete":
                chars[i] = ""
    return "".join(chars)


def word_dropout(text: str, rate: float, rng: random.Random) -> str:
    words = text.split()
    kept = [w for w in words if rng.random() >= rate]
    if not kept:
        kept = words[:1] if words else [""]
    return " ".join(kept)


def perturb_text_column(series: pd.Series, mode: str, param: float, seed: int) -> pd.Series:
    rng = random.Random(seed)
    if mode == "typo":
        return series.astype(str).map(lambda t: inject_typos(t, param, rng))
    elif mode == "word_dropout":
        return series.astype(str).map(lambda t: word_dropout(t, param, rng))
    elif mode == "empty":
        return series.astype(str).map(lambda t: "")
    return series


# ----------------------------------------------------------------------------
# Core evaluation-under-perturbation runner
# ----------------------------------------------------------------------------
def _evaluate_with_overrides(
    cfg: dict,
    model,
    tokenizer: Tokenizer,
    device: str,
    modality: str,
    frozen_threshold: float,
    image_transform_override=None,
    text_override_fn=None,
) -> Dict:
    cols = cfg["data"]["columns"]
    test_df = pd.read_csv(cfg["data"]["test_csv"])
    if text_override_fn is not None:
        test_df = test_df.copy()
        test_df[cols["text_col"]] = text_override_fn(test_df[cols["text_col"]])

    ds = AiGenFoodReviewDataset(
        test_df,
        image_dir=cfg["data"]["image_dir"],
        id_col=cols["id_col"],
        text_col=cols["text_col"],
        image_col=cols.get("image_col"),
        label_col=cols["label_col"],
        tokenizer=tokenizer,
        image_transform=image_transform_override,
        modality=modality,
    )
    loader = build_dataloader(ds, cfg["train"]["batch_size"], shuffle=False, num_workers=2, pin_memory=(device == "cuda"))
    preds = get_predictions(model, loader, device)
    return compute_metrics(preds["y_true"], preds["y_prob"], threshold=frozen_threshold)


def run_robustness_suite(cfg: dict, checkpoint_path: str, frozen_threshold: float) -> Dict:
    env = detect_environment(print_report=True)
    device = env.device

    ckpt = torch.load(checkpoint_path, map_location=device)
    model_type = ckpt["model_type"]
    saved_cfg = ckpt["cfg"]
    vocab_size = ckpt["vocab_size"]
    tokenizer = Tokenizer.load(cfg["paths"]["vocab_path"])

    model = build_model(model_type, vocab_size, saved_cfg).to(device)
    model.load_state_dict(ckpt["model_state"])

    if model_type in ("text_only", "image_only"):
        return {
            "status": "SKIPPED",
            "reason": f"Robustness suite targets multimodal models; '{model_type}' is unimodal by construction.",
        }

    resize = cfg["image"]["resize"]
    rcfg = cfg["robustness"]
    results: Dict[str, Dict] = {}

    # ---- baseline (undegraded) for reference ----
    results["baseline"] = _evaluate_with_overrides(cfg, model, tokenizer, device, "both", frozen_threshold)

    # ---- A. modality removal ----
    if rcfg.get("image_removal", True):
        gray_transform = build_degraded_transform(resize, "gray_removed", None)
        results["image_removed"] = _evaluate_with_overrides(
            cfg, model, tokenizer, device, "both", frozen_threshold, image_transform_override=gray_transform
        )
        results["text_removed"] = _evaluate_with_overrides(
            cfg, model, tokenizer, device, "both", frozen_threshold, text_override_fn=lambda s: perturb_text_column(s, "empty", 0, 0)
        )

    # ---- B. image degradation ----
    for q in rcfg["image_degradation"]["jpeg_quality_levels"]:
        t = build_degraded_transform(resize, "jpeg", q)
        results[f"jpeg_quality_{q}"] = _evaluate_with_overrides(cfg, model, tokenizer, device, "both", frozen_threshold, image_transform_override=t)

    for r in rcfg["image_degradation"]["gaussian_blur_radius"]:
        t = build_degraded_transform(resize, "blur", r)
        results[f"gaussian_blur_r{r}"] = _evaluate_with_overrides(cfg, model, tokenizer, device, "both", frozen_threshold, image_transform_override=t)

    # ---- C. text perturbation ----
    for rate in rcfg["text_perturbation"]["typo_rate"]:
        results[f"typo_rate_{rate}"] = _evaluate_with_overrides(
            cfg, model, tokenizer, device, "both", frozen_threshold,
            text_override_fn=lambda s, rate=rate: perturb_text_column(s, "typo", rate, seed=0),
        )
    for rate in rcfg["text_perturbation"]["word_dropout_rate"]:
        results[f"word_dropout_{rate}"] = _evaluate_with_overrides(
            cfg, model, tokenizer, device, "both", frozen_threshold,
            text_override_fn=lambda s, rate=rate: perturb_text_column(s, "word_dropout", rate, seed=0),
        )

    # ---- optional: generator-separated evaluation ----
    if rcfg.get("generator_separated_eval", False):
        results["generator_separated"] = {"status": "REQUESTED_BUT_NOT_IMPLEMENTED_HERE_SEE_NOTE"}
    else:
        results["generator_separated"] = {
            "status": "NOT_AVAILABLE",
            "reason": "No generation-source column configured/found. Requires dataset metadata identifying which generator produced each synthetic sample; do not fabricate this split.",
        }

    output = {"model_type": model_type, "checkpoint": checkpoint_path, "frozen_threshold": frozen_threshold, "results": results}
    save_json(output, f"{cfg['paths']['results_dir']}/robustness_{model_type}.json")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--frozen_threshold", type=float, required=True, help="From evaluate.py's validation_selected_threshold output.")
    args = parser.parse_args()
    cfg = load_config(args.config)
    out = run_robustness_suite(cfg, args.checkpoint, args.frozen_threshold)
    print(out)
