"""
metrics.py
----------
All metrics required by spec section 9, plus bootstrap CI utilities for
section 20 (statistical analysis).

Positive class = 1 = machine-generated, per spec.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """
    y_true: (N,) binary {0,1}
    y_prob: (N,) predicted probability of class 1 (machine-generated)
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    # ROC-AUC / PR-AUC require both classes present; guard against the
    # degenerate case (shouldn't happen on the real dataset, but a robustness
    # subset or tiny debug run might trigger it).
    try:
        roc_auc = roc_auc_score(y_true, y_prob)
    except ValueError:
        roc_auc = float("nan")
    try:
        pr_auc = average_precision_score(y_true, y_prob)
    except ValueError:
        pr_auc = float("nan")

    return {
        "threshold": threshold,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
    }


def select_threshold_on_validation(
    y_true_val: np.ndarray, y_prob_val: np.ndarray, metric: str = "f1", grid_step: float = 0.01
) -> Tuple[float, float]:
    """
    Scans thresholds on VALIDATION predictions only and returns the
    threshold maximizing `metric`. The caller must freeze this threshold
    before touching the test set (see evaluate.py).
    """
    thresholds = np.arange(0.01, 1.0, grid_step)
    best_thresh, best_score = 0.5, -1.0
    for t in thresholds:
        m = compute_metrics(y_true_val, y_prob_val, threshold=t)
        score = m[metric]
        if score > best_score:
            best_score = score
            best_thresh = float(t)
    return best_thresh, best_score


def paired_bootstrap_test(
    y_true: np.ndarray,
    y_prob_a: np.ndarray,
    y_prob_b: np.ndarray,
    metric_fn=f1_score,
    threshold: float = 0.5,
    n_bootstrap: int = 5000,
    seed: int = 0,
) -> Dict[str, float]:
    """
    Paired bootstrap over the SAME test predictions for two models (A vs B),
    used for the concat-vs-gated comparison (spec section 20).

    Returns: observed difference (B - A), 95% CI on the difference, and the
    fraction of bootstrap resamples where B >= A (a one-sided empirical
    p-value proxy: p = 1 - fraction(B > A) for "B is better").
    """
    rng = np.random.RandomState(seed)
    y_true = np.asarray(y_true).astype(int)
    y_prob_a = np.asarray(y_prob_a)
    y_prob_b = np.asarray(y_prob_b)
    n = len(y_true)

    def _score(yt, yp):
        pred = (yp >= threshold).astype(int)
        return metric_fn(yt, pred, zero_division=0) if metric_fn in (f1_score, precision_score, recall_score) else metric_fn(yt, pred)

    observed_diff = _score(y_true, y_prob_b) - _score(y_true, y_prob_a)

    diffs = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.randint(0, n, size=n)
        diffs[i] = _score(y_true[idx], y_prob_b[idx]) - _score(y_true[idx], y_prob_a[idx])

    ci_lower, ci_upper = np.percentile(diffs, [2.5, 97.5])
    # one-sided empirical p-value that B is NOT better than A
    p_value_b_better = float(np.mean(diffs <= 0))

    return {
        "method": "paired_bootstrap_over_test_predictions",
        "n_bootstrap": n_bootstrap,
        "observed_diff_B_minus_A": float(observed_diff),
        "ci_95_lower": float(ci_lower),
        "ci_95_upper": float(ci_upper),
        "p_value_B_not_better_than_A": p_value_b_better,
        "significant_at_0.05": bool(ci_lower > 0 or ci_upper < 0),
    }


def mean_std_across_seeds(metric_values: list) -> Dict[str, float]:
    arr = np.asarray(metric_values, dtype=float)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=1) if len(arr) > 1 else 0.0), "n": len(arr)}
