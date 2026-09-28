"""
hparam_search.py
------------------
PHASE (part of 6/7). A compact grid search over the candidate values in
spec section 7, using TRAIN+VALIDATION only. The test set is never loaded
by this script at all -- not just "not scored", literally never read --
to make it structurally impossible to leak into hyperparameter decisions.

Search space (from config.yaml -> hparam_search):
  embedding_dim, lstm_hidden, dropout, lr_new_layers, lr_finetune_layers

To keep this tractable (spec explicitly says "do not perform an enormous
expensive search"), this script does NOT do a full cartesian grid over all
five dimensions (3*3*3*2*2 = 108 runs, infeasible on a T4 for a paper
timeline). Instead it does a two-stage compact search:
  Stage 1: vary {embedding_dim, lstm_hidden, dropout} with lr fixed at the
           config default -- selects best of 3*3*3=27... still too many.
  Stage 2 default: a curated small grid (see `DEFAULT_COMPACT_GRID`) of
           ~6-8 combinations, which is what actually runs unless
           `--full_grid` is passed (full grid available for completeness /
           reviewer requests, off by default).

Every trial's validation score is logged; the best config (by val F1) is
saved to results/best_hparams.json. This file is what train.py's
"principal configuration" should subsequently be set to, by manually
copying the values into config.yaml (kept manual and explicit rather than
auto-overwritten, so the paper's config.yaml always reflects a
human-reviewed decision).
"""
from __future__ import annotations

import argparse
import copy
import itertools
from typing import Dict, List

from train import train_one_run
from utils import get_logger, load_config, save_json

# A small, explicit, reproducible grid -- chosen to cover the main axes of
# variation (capacity via embedding/lstm size, regularization via dropout)
# without the combinatorial explosion of the full cartesian product.
DEFAULT_COMPACT_GRID: List[Dict] = [
    {"embedding_dim": 128, "lstm_hidden": 128, "dropout": 0.3},
    {"embedding_dim": 128, "lstm_hidden": 128, "dropout": 0.4},
    {"embedding_dim": 128, "lstm_hidden": 128, "dropout": 0.5},
    {"embedding_dim": 64, "lstm_hidden": 64, "dropout": 0.4},
    {"embedding_dim": 256, "lstm_hidden": 256, "dropout": 0.4},
    {"embedding_dim": 128, "lstm_hidden": 256, "dropout": 0.4},
]


def _full_grid(search_cfg: dict) -> List[Dict]:
    keys = ["embedding_dim", "lstm_hidden", "dropout"]
    values = [search_cfg[k] for k in keys]
    combos = list(itertools.product(*values))
    return [dict(zip(keys, c)) for c in combos]


def run_search(cfg: dict, model_type: str, full_grid: bool = False, seed: int = 42) -> Dict:
    logger = get_logger("hparam_search", cfg["paths"]["logs_dir"])
    search_cfg = cfg["hparam_search"]
    grid = _full_grid(search_cfg) if full_grid else DEFAULT_COMPACT_GRID
    logger.info(f"Running {'FULL' if full_grid else 'COMPACT'} grid search: {len(grid)} trials.")

    trial_results = []
    for i, params in enumerate(grid):
        trial_cfg = copy.deepcopy(cfg)
        trial_cfg["model"]["text"]["embedding_dim"] = params["embedding_dim"]
        trial_cfg["text"]["embedding_dim"] = params["embedding_dim"]
        trial_cfg["model"]["text"]["lstm_hidden"] = params["lstm_hidden"]
        trial_cfg["model"]["classifier"]["dropout"] = params["dropout"]
        # keep epochs modest during search to keep it "compact" per spec;
        # early stopping still governs actual duration.
        trial_cfg["train"]["max_epochs"] = min(trial_cfg["train"]["max_epochs"], 15)

        logger.info(f"Trial {i+1}/{len(grid)}: {params}")
        result = train_one_run(trial_cfg, seed, model_type, logger)
        trial_results.append({"params": params, "best_val_f1": result["best_val_f1"]})

    best_trial = max(trial_results, key=lambda r: r["best_val_f1"])
    output = {
        "model_type": model_type,
        "search_seed": seed,
        "grid_type": "full" if full_grid else "compact",
        "all_trials": trial_results,
        "best_params": best_trial["params"],
        "best_val_f1": best_trial["best_val_f1"],
        "note": "Selected using TRAIN+VALIDATION only. Test set was never loaded by this script.",
    }
    save_json(output, search_cfg["output_file"])
    logger.info(f"Best hyperparameters: {best_trial}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--model_type", type=str, default="gated")
    parser.add_argument("--full_grid", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    cfg = load_config(args.config)
    run_search(cfg, args.model_type, full_grid=args.full_grid, seed=args.seed)
