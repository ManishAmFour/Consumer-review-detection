"""
aggregate_results.py
---------------------
PHASE 16-17 / spec sections 19, 20, 27, 28.

Reads ONLY files that train.py / evaluate.py / seed_experiments.py /
compute_cost.py / robustness.py / error_analysis.py / interpretability.py
have already written to results/, and assembles:

  - results/final_results.csv          (Table A: main comparison, mean+-SD across seeds)
  - results/statistical_comparison.json (concat vs gated paired bootstrap, section 20)
  - research_report.md                  (full report, section 27)
  - "Results for Paper" section printed to stdout (section 28)

This script performs NO training and NO estimation. If a required
upstream file is missing, it reports that fact in the output rather than
inventing a number. Every number that DOES appear in the output carries an
explicit source path so it is traceable back to the executed experiment
that produced it (spec section 28's traceability requirement).

Usage:
    python src/aggregate_results.py --config configs/config.yaml
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from metrics import paired_bootstrap_test
from utils import load_config, load_json, save_json

MODEL_DISPLAY_NAMES = {
    "text_only": "Bi-LSTM (text-only)",
    "image_only": "ResNet-50 (image-only)",
    "concat": "Concat Fusion",
    "gated": "Reliability-Gated Fusion",
    "gated_finetuned": "Gated + Fine-tuned ResNet",
}
MODEL_ORDER = ["text_only", "image_only", "concat", "gated", "gated_finetuned"]


def _try_load(path: str) -> Optional[dict]:
    if os.path.exists(path):
        return load_json(path)
    return None


def build_final_results_table(results_dir: str) -> pd.DataFrame:
    rows = []
    sources = {}
    for model_type in MODEL_ORDER:
        seed_agg_path = os.path.join(results_dir, f"seed_results_{model_type}.json")
        agg = _try_load(seed_agg_path)
        if agg is None:
            rows.append({"model_type": MODEL_DISPLAY_NAMES[model_type], "status": "NOT YET RUN",
                         "source": f"MISSING: {seed_agg_path}"})
            continue
        block = agg["test_results_validation_selected_threshold_agg"]
        row = {"model_type": MODEL_DISPLAY_NAMES[model_type]}
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            m = block[metric]
            row[metric] = f"{m['mean']:.4f} +/- {m['std']:.4f}"
            row[f"{metric}_mean"] = m["mean"]
            row[f"{metric}_std"] = m["std"]
        row["n_seeds"] = block["accuracy"]["n"]
        row["source"] = seed_agg_path
        rows.append(row)
        sources[model_type] = seed_agg_path

    df = pd.DataFrame(rows)
    return df


def build_computational_table(results_dir: str) -> Optional[pd.DataFrame]:
    path = os.path.join(results_dir, "computational_cost.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df["model_type"] = df["model_type"].map(lambda m: MODEL_DISPLAY_NAMES.get(m, m))
    return df


def build_ablation_table(results_dir: str) -> pd.DataFrame:
    """Same underlying numbers as final_results, re-labeled per spec section 11's A-E naming."""
    df = build_final_results_table(results_dir)
    label_map = {
        "Bi-LSTM (text-only)": "A. Text-only",
        "ResNet-50 (image-only)": "B. Image-only",
        "Concat Fusion": "C. Text+Image (concatenation)",
        "Reliability-Gated Fusion": "D. Text+Image (reliability gate)",
        "Gated + Fine-tuned ResNet": "E. Reliability gate + ResNet fine-tuning",
    }
    df["ablation_label"] = df["model_type"].map(label_map)
    return df


def statistical_comparison_concat_vs_gated(results_dir: str, n_bootstrap: int = 2000) -> Dict:
    """
    Spec section 20: concat vs gated, paired bootstrap over the SAME test
    set. Uses seed=42's predictions for both models by default (the first
    of the three principal seeds) since a paired bootstrap requires the
    exact same test rows scored by both models -- seed choice here affects
    only WHICH model checkpoints are compared, not the test set itself
    (identical official test split for every seed/model).
    """
    concat_path = os.path.join(results_dir, "predictions_concat_seed42.csv")
    gated_path = os.path.join(results_dir, "predictions_gated_seed42.csv")
    if not (os.path.exists(concat_path) and os.path.exists(gated_path)):
        return {
            "status": "NOT_AVAILABLE",
            "reason": f"Requires both {concat_path} and {gated_path} from evaluate.py runs.",
        }

    df_concat = pd.read_csv(concat_path)
    df_gated = pd.read_csv(gated_path)
    merged = df_concat.merge(df_gated, on="id", suffixes=("_concat", "_gated"))
    assert (merged["y_true_concat"] == merged["y_true_gated"]).all(), "Test set mismatch between models!"

    result = paired_bootstrap_test(
        merged["y_true_concat"].values,
        merged["y_prob_concat"].values,
        merged["y_prob_gated"].values,
        n_bootstrap=n_bootstrap,
    )
    result["status"] = "OK"
    result["n_test_samples"] = int(len(merged))
    result["interpretation"] = (
        "observed_diff_B_minus_A > 0 means Gated Fusion outperformed Concat Fusion on F1 "
        "for this seed/test set. significant_at_0.05=True only if the 95% CI on the "
        "difference excludes zero."
    )
    return result


def generate_research_report(cfg: dict, out_path: str = "research_report.md") -> None:
    results_dir = cfg["paths"]["results_dir"]

    dataset_audit = _try_load(os.path.join(results_dir, "dataset_audit.json"))
    leakage = _try_load(os.path.join(results_dir, "leakage_report.json"))
    best_hparams = _try_load(cfg["hparam_search"]["output_file"])
    final_df = build_final_results_table(results_dir)
    ablation_df = build_ablation_table(results_dir)
    comp_df = build_computational_table(results_dir)
    stat_comp = statistical_comparison_concat_vs_gated(results_dir)

    robustness_files = sorted(glob.glob(os.path.join(results_dir, "robustness_*.json")))
    error_analysis = _try_load(os.path.join(results_dir, "error_analysis.json"))
    interpretability = _try_load(os.path.join(results_dir, "interpretability.json"))

    lines: List[str] = []
    lines.append("# Research Report")
    lines.append("")
    lines.append("**A Multimodal Bi-LSTM-ResNet-50 Framework with Reliability-Gated Fusion "
                 "for Detecting Machine-Generated Restaurant Reviews**")
    lines.append("")
    lines.append("> Every number below is either pulled directly from a JSON/CSV file written by an "
                 "actually-executed script in `src/`, or explicitly marked as NOT YET RUN / NOT AVAILABLE. "
                 "Nothing in this report is estimated or fabricated.")
    lines.append("")

    lines.append("## 1. Dataset Audit")
    if dataset_audit:
        lines.append(f"Status: `{dataset_audit.get('status')}`  (source: `results/dataset_audit.json`)")
        lines.append("")
        lines.append("See `results/dataset_audit.json` for full per-CSV column detection, class "
                     "distributions, missing-image counts, and duplicate-ID counts.")
    else:
        lines.append("**NOT YET RUN.** Run `python src/dataset_audit.py --config configs/config.yaml` first.")
    lines.append("")

    lines.append("## 2. Leakage Audit")
    if leakage:
        lines.append(f"Status: `{leakage.get('status')}`  (source: `results/leakage_report.json`)")
        if leakage.get("leakage_flags"):
            lines.append(f"Flags: {leakage['leakage_flags']}")
    else:
        lines.append("**NOT YET RUN.** Run `python src/leakage_check.py --config configs/config.yaml` first.")
    lines.append("")

    lines.append("## 3-4. Training Configuration & Hyperparameters")
    lines.append("Principal training configuration: see `configs/config.yaml` (`train:` block).")
    if best_hparams:
        lines.append(f"Selected hyperparameters (train+val only, source: `{cfg['hparam_search']['output_file']}`): "
                     f"`{best_hparams.get('best_params')}` (val F1 = {best_hparams.get('best_val_f1'):.4f})")
    else:
        lines.append("Hyperparameter search NOT YET RUN. Run `src/hparam_search.py`.")
    lines.append("")

    lines.append("## 5-6. Model Architecture & Parameter Counts")
    if comp_df is not None:
        lines.append(comp_df.to_markdown(index=False))
    else:
        lines.append("**NOT YET RUN.** Run `python src/compute_cost.py` against trained checkpoints.")
    lines.append("")

    lines.append("## 7-9. Test Results (mean +/- SD across seeds, validation-selected threshold)")
    lines.append(final_df.to_markdown(index=False) if not final_df.empty else "No results yet.")
    lines.append("")

    lines.append("## 13. Ablation Results")
    lines.append(ablation_df.to_markdown(index=False) if not ablation_df.empty else "No results yet.")
    lines.append("")

    lines.append("## 14. Robustness Results")
    if robustness_files:
        for rf in robustness_files:
            lines.append(f"- `{rf}`")
    else:
        lines.append("**NOT YET RUN.** Run `python src/robustness.py` on frozen checkpoints.")
    lines.append("")

    lines.append("## 15. Computational Analysis")
    lines.append("See section 5-6 table above and `results/computational_cost.csv` / `.json`.")
    lines.append("")

    lines.append("## 16. Error Analysis")
    if error_analysis:
        lines.append(f"See `results/error_analysis.csv` / `.json`. Note: {error_analysis.get('note')}")
    else:
        lines.append("**NOT YET RUN.** Run `python src/error_analysis.py`.")
    lines.append("")

    lines.append("## 17. Statistical Comparison (Concat vs Gated Fusion)")
    lines.append(f"```json\n{json.dumps(stat_comp, indent=2)}\n```")
    lines.append("")

    lines.append("## Interpretability (Gate Analysis)")
    if interpretability:
        lines.append(f"See `results/interpretability.json`. {interpretability['gate_distribution'].get('disclaimer', '')}")
    else:
        lines.append("**NOT YET RUN.** Run `python src/interpretability.py`.")
    lines.append("")

    lines.append("## 18. Limitations")
    lines.append(
        "- Results reflect only the executed seeds/configurations recorded in `results/`; if fewer than "
        "3 seeds are present for a model, that model's mean +/- SD is not yet a complete reproducibility check.\n"
        "- The gate's values are descriptive statistics only; they are not validated causal explanations.\n"
        "- Near-duplicate text detection uses a heuristic blocking approach (see `leakage_report.json`) and "
        "is not exhaustive.\n"
        "- External benchmark numbers (FLAVA, PosAtt-BiLSTM, BERT+ResNet-50) are cited from their original "
        "publications for context only and were not reproduced here."
    )
    lines.append("")

    lines.append("## 19. Reproducibility Information")
    lines.append(
        "- Seeds used: see `configs/config.yaml` -> `seeds`.\n"
        "- Full command sequence: see `README.md` / `run_pipeline.sh`.\n"
        "- Environment used for each run is logged inside every `results/train_history_*.json` "
        "(`device`, `gpu_name`) and every `logs/*.log` file."
    )

    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Research report written to {out_path}")


def main(config_path: str):
    cfg = load_config(config_path)
    results_dir = cfg["paths"]["results_dir"]
    os.makedirs(results_dir, exist_ok=True)

    final_df = build_final_results_table(results_dir)
    final_df.to_csv(os.path.join(results_dir, "final_results.csv"), index=False)

    ablation_df = build_ablation_table(results_dir)
    ablation_df.to_csv(os.path.join(results_dir, "ablation_results.csv"), index=False)

    stat_comp = statistical_comparison_concat_vs_gated(results_dir)
    save_json(stat_comp, os.path.join(results_dir, "statistical_comparison.json"))

    generate_research_report(cfg)

    print("\n=== Results for Paper ===")
    print("\nTABLE A: Main performance comparison\n")
    print(final_df.to_string(index=False))
    print("\nTABLE B: Ablation study\n")
    print(ablation_df.to_string(index=False))
    comp_df = build_computational_table(results_dir)
    print("\nTABLE C: Computational cost\n")
    print(comp_df.to_string(index=False) if comp_df is not None else "NOT YET RUN")
    print("\nStatistical comparison (Concat vs Gated):\n")
    print(json.dumps(stat_comp, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    args = parser.parse_args()
    main(args.config)
