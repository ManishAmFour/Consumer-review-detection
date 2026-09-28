"""
interpretability.py
--------------------
Spec section 22. Analyzes the reliability gate's behavior descriptively --
distribution of gate values overall and split by true class -- explicitly
NOT as a causal explanation of individual predictions (per spec sections 4
and 22, and the warning already embedded in fusion.py).

This script only consumes gate values that were actually produced during a
real evaluate.py run (saved in the predictions CSV's `gate_mean` column,
one scalar per sample = mean over the 256-dim gate vector for that sample).
It does not run the model itself and does not fabricate gate values.

Modality-perturbation performance (image removal, text perturbation) is
already produced by robustness.py; this script simply cross-references
those numbers rather than recomputing them, so there is a single source of
truth for "what happens when a modality is degraded".

Usage:
    python src/interpretability.py --predictions results/predictions_gated_seed42.csv \
        --robustness_json results/robustness_gated.json
"""
from __future__ import annotations

import argparse
import json
from typing import Dict, Optional

import numpy as np
import pandas as pd

from utils import save_json

DISCLAIMER = (
    "The reliability gate is a learned representation-weighting mechanism. "
    "These statistics describe HOW the gate behaves on average; they are "
    "NOT causal explanations of any individual prediction, and should not "
    "be reported in the paper as such."
)


def analyze_gate_distribution(predictions_csv: str) -> Dict:
    df = pd.read_csv(predictions_csv)
    if "gate_mean" not in df.columns:
        return {
            "status": "NOT_AVAILABLE",
            "reason": "predictions CSV has no 'gate_mean' column -- this checkpoint is not a "
                      "gated-fusion model, or evaluate.py was run before the gate-logging change.",
        }

    overall = df["gate_mean"].describe().to_dict()
    by_class = {}
    for label, name in [(0, "authentic"), (1, "machine_generated")]:
        sub = df.loc[df["y_true"] == label, "gate_mean"]
        by_class[name] = sub.describe().to_dict() if len(sub) else {"n": 0}

    # simple correlation between gate value and correctness -- descriptive only
    y_pred = (df["y_prob"] >= 0.5).astype(int)
    correct = (y_pred == df["y_true"]).astype(int)
    corr = float(np.corrcoef(df["gate_mean"], correct)[0, 1]) if df["gate_mean"].nunique() > 1 else float("nan")

    return {
        "status": "OK",
        "n_samples": int(len(df)),
        "overall_gate_stats": overall,
        "gate_stats_by_true_class": by_class,
        "pearson_corr_gate_vs_correctness": corr,
        "disclaimer": DISCLAIMER,
    }


def summarize_modality_reliance(robustness_json_path: Optional[str]) -> Dict:
    if not robustness_json_path:
        return {"status": "NOT_PROVIDED"}
    with open(robustness_json_path) as f:
        data = json.load(f)
    results = data.get("results", {})
    baseline_f1 = results.get("baseline", {}).get("f1")
    summary = {"baseline_f1": baseline_f1, "deltas": {}}
    for key, val in results.items():
        if key == "baseline" or not isinstance(val, dict) or "f1" not in val:
            continue
        summary["deltas"][key] = {
            "f1": val["f1"],
            "delta_vs_baseline": (val["f1"] - baseline_f1) if baseline_f1 is not None else None,
        }
    summary["note"] = (
        "Larger negative delta = model relies more heavily on that modality/aspect. "
        "This is an empirical robustness result, not a gate-based causal claim."
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=str, required=True)
    parser.add_argument("--robustness_json", type=str, default=None)
    parser.add_argument("--out", type=str, default="results/interpretability.json")
    args = parser.parse_args()

    gate_analysis = analyze_gate_distribution(args.predictions)
    modality_summary = summarize_modality_reliance(args.robustness_json)

    output = {"gate_distribution": gate_analysis, "modality_reliance_via_robustness": modality_summary}
    save_json(output, args.out)
    print(json.dumps(output, indent=2, default=str))
