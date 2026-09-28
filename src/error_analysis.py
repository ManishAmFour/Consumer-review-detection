"""
error_analysis.py
------------------
PHASE 17 / spec section 21. Extracts representative TP/TN/FP/FN examples
from a REAL predictions CSV (produced by evaluate.py) and assigns each a
best-guess error category from the fixed taxonomy in the spec. Category
assignment here is a simple rule-of-thumb heuristic over available fields
(text length, whether the image was missing/degraded, prediction
confidence) -- it is explicitly NOT a claim of ground truth causation, and
each row is left for a human (the paper's author) to review and correct.

No personal information is included: only the review text itself (already
present in the dataset) and the associated numeric fields are kept -- no
reviewer names, emails, or other metadata are pulled in even if present in
the source CSV, per spec section 21's privacy requirement.

Usage:
    python src/error_analysis.py --config configs/config.yaml \
        --predictions results/predictions_gated_seed42.csv --threshold 0.5 --n_examples 10
"""
from __future__ import annotations

import argparse
from typing import Dict, List

import pandas as pd

from utils import load_config, save_json


CATEGORY_NOTE = (
    "Category is a heuristic suggestion only (based on text length / gate "
    "value / confidence), not a verified root cause. A human reviewer "
    "should read the actual text/image before citing a category in the paper."
)


def _guess_category(row: pd.Series, error_type: str) -> str:
    """
    Rule-of-thumb category assignment from the fixed taxonomy in spec
    section 21. This is a heuristic starting point for manual review, not
    an automated ground-truth labeler.
    """
    text_len = len(str(row.get("text", "")).split())
    gate_mean = row.get("gate_mean", None)
    prob = row.get("y_prob", 0.5)
    confidence = abs(prob - 0.5) * 2  # 0 = maximally uncertain, 1 = maximally confident

    if confidence < 0.15:
        return "5. Insufficient context (low model confidence)"
    if text_len < 6:
        return "1. Linguistic ambiguity (very short text)"
    if gate_mean is not None and gate_mean > 0.85:
        return "2. Irrelevant image (model relied almost entirely on text)"
    if gate_mean is not None and gate_mean < 0.15:
        return "3. Low image quality / weak text signal (model relied almost entirely on image)"
    if error_type in ("FP", "FN"):
        return "4. Cross-modal inconsistency (candidate; verify manually)"
    return "6. Possible annotation ambiguity (default; verify manually)"


def run_error_analysis(predictions_csv: str, source_df: pd.DataFrame, text_col: str,
                        threshold: float, n_examples: int) -> Dict:
    preds = pd.read_csv(predictions_csv)
    merged = preds.merge(source_df[[c for c in source_df.columns if c in ("id", text_col)]],
                          on="id", how="left") if "id" in source_df.columns else preds
    if text_col in merged.columns:
        merged = merged.rename(columns={text_col: "text"})

    merged["y_pred"] = (merged["y_prob"] >= threshold).astype(int)

    def _bucket(r):
        if r["y_true"] == 1 and r["y_pred"] == 1:
            return "TP"
        if r["y_true"] == 0 and r["y_pred"] == 0:
            return "TN"
        if r["y_true"] == 0 and r["y_pred"] == 1:
            return "FP"
        return "FN"

    merged["error_bucket"] = merged.apply(_bucket, axis=1)

    examples: Dict[str, List[dict]] = {}
    for bucket in ["TP", "TN", "FP", "FN"]:
        subset = merged[merged["error_bucket"] == bucket].copy()
        # representative = closest-to-decision-boundary for FP/FN (most informative
        # errors), most-confident-correct for TP/TN
        abs_diff = (subset["y_prob"] - threshold).abs()
        if bucket in ("FP", "FN"):
            # most informative errors = closest to the decision boundary -> ascending abs_diff
            subset["_sort_key"] = abs_diff
        else:
            # most confident correct predictions -> descending abs_diff (encoded as ascending -abs_diff)
            subset["_sort_key"] = -abs_diff
        subset = subset.sort_values("_sort_key").head(n_examples)

        rows = []
        for _, r in subset.iterrows():
            row_out = {
                "id": r.get("id"),
                "y_true": int(r["y_true"]),
                "y_prob": float(r["y_prob"]),
                "text": r.get("text", None),
            }
            if "gate_mean" in r:
                row_out["gate_mean"] = float(r["gate_mean"]) if pd.notna(r["gate_mean"]) else None
            row_out["suggested_category"] = _guess_category(r, bucket)
            rows.append(row_out)
        examples[bucket] = rows

    return {"examples": examples, "note": CATEGORY_NOTE, "threshold_used": threshold}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--predictions", type=str, required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--n_examples", type=int, default=10)
    args = parser.parse_args()

    cfg = load_config(args.config)
    cols = cfg["data"]["columns"]
    test_df = pd.read_csv(cfg["data"]["test_csv"])
    test_df = test_df.rename(columns={cols["id_col"]: "id"})

    result = run_error_analysis(args.predictions, test_df, cols["text_col"], args.threshold, args.n_examples)
    save_json(result, f"{cfg['paths']['results_dir']}/error_analysis.json")

    # flat CSV too, for easy spreadsheet review
    rows = []
    for bucket, examples in result["examples"].items():
        for ex in examples:
            rows.append({"bucket": bucket, **ex})
    pd.DataFrame(rows).to_csv(f"{cfg['paths']['results_dir']}/error_analysis.csv", index=False)
    print(f"Error analysis written to {cfg['paths']['results_dir']}/error_analysis.[json|csv]")
