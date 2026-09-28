"""
seed_experiments.py
--------------------
PHASE 13. Runs a given model_type across cfg['seeds'] (default [42, 123, 2024]),
training independently each time, evaluating once on test AFTER the
configuration is frozen, and aggregating mean +/- std -- never reporting a
single best seed as the final number (spec section 8/24).

Usage:
    python src/seed_experiments.py --config configs/config.yaml --model_type gated
"""
from __future__ import annotations

import argparse
from typing import Dict, List

import pandas as pd

from evaluate import evaluate_checkpoint
from metrics import mean_std_across_seeds
from train import train_one_run
from utils import get_logger, load_config, save_json


def run_seed_experiments(cfg: dict, model_type: str) -> Dict:
    logger = get_logger(f"seed_experiments_{model_type}", cfg["paths"]["logs_dir"])
    seeds: List[int] = cfg["seeds"]

    per_seed_train, per_seed_eval = [], []
    for seed in seeds:
        logger.info(f"=== Training {model_type}, seed={seed} ===")
        train_result = train_one_run(cfg, seed, model_type, logger)
        per_seed_train.append(train_result)

        logger.info(f"=== Evaluating {model_type}, seed={seed} (test set touched ONCE here) ===")
        eval_result = evaluate_checkpoint(cfg, train_result["checkpoint_path"])
        per_seed_eval.append(eval_result)

    # aggregate mean +/- std across seeds, for BOTH thresholding protocols
    agg = {"model_type": model_type, "seeds": seeds, "per_seed": per_seed_eval}
    for threshold_key in ["test_results_default_threshold_0.5", "test_results_validation_selected_threshold"]:
        agg[threshold_key + "_agg"] = {}
        for metric_name in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            values = [r[threshold_key][metric_name] for r in per_seed_eval]
            agg[threshold_key + "_agg"][metric_name] = mean_std_across_seeds(values)

    save_json(agg, f"{cfg['paths']['results_dir']}/seed_results_{model_type}.json")

    # flat CSV row per seed for easy aggregation across all 5 models later
    rows = []
    for r in per_seed_eval:
        row = {"model_type": model_type, "seed": r["seed"]}
        for k, v in r["test_results_default_threshold_0.5"].items():
            row[f"default_{k}"] = v
        for k, v in r["test_results_validation_selected_threshold"].items():
            row[f"frozen_{k}"] = v
        rows.append(row)
    df = pd.DataFrame(rows)
    csv_path = f"{cfg['paths']['results_dir']}/seed_results_{model_type}.csv"
    df.to_csv(csv_path, index=False)
    logger.info(f"Seed experiment results written to {csv_path}")
    return agg


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument(
        "--model_type", type=str, required=True,
        choices=["text_only", "image_only", "concat", "gated", "gated_finetuned"],
    )
    args = parser.parse_args()
    cfg = load_config(args.config)
    run_seed_experiments(cfg, args.model_type)
