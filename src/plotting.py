"""
plotting.py
-----------
Generates every plot required by spec sections 9 and 18, from REAL saved
results/predictions only. No plot in this file synthesizes data -- each
function takes arrays/DataFrames that must already exist on disk from an
actual run (train.py / evaluate.py / seed_experiments.py / robustness.py).

Usage examples:
    python src/plotting.py confusion_matrix --predictions results/predictions_gated_seed42.csv --threshold 0.5
    python src/plotting.py roc_pr --predictions results/predictions_gated_seed42.csv
    python src/plotting.py training_curves --history results/train_history_gated_seed42.json
    python src/plotting.py model_comparison --final_results results/final_results.csv
    python src/plotting.py robustness --robustness_json results/robustness_gated.json
"""
from __future__ import annotations

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve

PLOTS_DIR = "plots"


def _ensure_dir():
    os.makedirs(PLOTS_DIR, exist_ok=True)


def plot_confusion_matrix(predictions_csv: str, threshold: float = 0.5, out_name: str = "confusion_matrix.png"):
    _ensure_dir()
    df = pd.read_csv(predictions_csv)
    y_true = df["y_true"].astype(int).values
    y_pred = (df["y_prob"].values >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    fig, ax = plt.subplots(figsize=(5, 4.5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Authentic (0)", "Machine-gen. (1)"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Authentic (0)", "Machine-gen. (1)"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title(f"Confusion Matrix (threshold={threshold})")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=14)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    out_path = os.path.join(PLOTS_DIR, out_name)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")
    return cm


def plot_roc_pr(predictions_csv: str, roc_name: str = "roc_curve.png", pr_name: str = "precision_recall_curve.png"):
    _ensure_dir()
    df = pd.read_csv(predictions_csv)
    y_true = df["y_true"].astype(int).values
    y_prob = df["y_prob"].values

    fpr, tpr, _ = roc_curve(y_true, y_prob)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(fpr, tpr, label="Model")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve"); ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, roc_name), dpi=150)
    plt.close(fig)

    prec, rec, _ = precision_recall_curve(y_true, y_prob)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(rec, prec)
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, pr_name), dpi=150)
    plt.close(fig)
    print(f"Saved {roc_name} and {pr_name} to {PLOTS_DIR}/")


def plot_training_curves(history_json: str, out_name: str = "training_curves.png"):
    _ensure_dir()
    with open(history_json) as f:
        result = json.load(f)
    hist = result["history"]
    epochs = range(1, len(hist["train_loss"]) + 1)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(epochs, hist["train_loss"], label="train")
    axes[0].plot(epochs, hist["val_loss"], label="val")
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("BCE Loss"); axes[0].set_title("Loss"); axes[0].legend()

    axes[1].plot(epochs, hist["train_f1"], label="train")
    axes[1].plot(epochs, hist["val_f1"], label="val")
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("F1"); axes[1].set_title("F1 Score"); axes[1].legend()

    fig.suptitle(f"{result.get('model_type', '')} (seed={result.get('seed', '')})")
    fig.tight_layout()
    out_path = os.path.join(PLOTS_DIR, out_name)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_model_comparison(final_results_csv: str, out_name: str = "model_comparison.png"):
    _ensure_dir()
    df = pd.read_csv(final_results_csv)
    metrics = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
    metrics = [m for m in metrics if m in df.columns]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(df))
    width = 0.8 / len(metrics)
    for i, m in enumerate(metrics):
        ax.bar(x + i * width, df[m], width=width, label=m)
    ax.set_xticks(x + width * (len(metrics) - 1) / 2)
    ax.set_xticklabels(df["model_type"] if "model_type" in df.columns else df.index, rotation=20, ha="right")
    ax.set_ylabel("Score")
    ax.set_title("Model Comparison (test set, real executed results)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    out_path = os.path.join(PLOTS_DIR, out_name)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_robustness(robustness_json: str, out_name: str = "robustness.png"):
    _ensure_dir()
    with open(robustness_json) as f:
        data = json.load(f)
    results = data["results"]
    keys, f1s = [], []
    for k, v in results.items():
        if isinstance(v, dict) and "f1" in v:
            keys.append(k)
            f1s.append(v["f1"])

    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = ["tab:green" if k == "baseline" else "tab:red" for k in keys]
    x = np.arange(len(keys))
    ax.bar(x, f1s, color=colors)
    ax.set_ylabel("F1 (test set)")
    ax.set_title(f"Robustness: {data.get('model_type', '')} under perturbation")
    ax.set_xticks(x)
    ax.set_xticklabels(keys, rotation=30, ha="right")
    ax.axhline(f1s[keys.index("baseline")] if "baseline" in keys else 0, color="gray", linestyle="--", linewidth=1)
    fig.tight_layout()
    out_path = os.path.join(PLOTS_DIR, out_name)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("confusion_matrix")
    p1.add_argument("--predictions", required=True)
    p1.add_argument("--threshold", type=float, default=0.5)

    p2 = sub.add_parser("roc_pr")
    p2.add_argument("--predictions", required=True)

    p3 = sub.add_parser("training_curves")
    p3.add_argument("--history", required=True)

    p4 = sub.add_parser("model_comparison")
    p4.add_argument("--final_results", required=True)

    p5 = sub.add_parser("robustness")
    p5.add_argument("--robustness_json", required=True)

    args = parser.parse_args()
    if args.command == "confusion_matrix":
        plot_confusion_matrix(args.predictions, args.threshold)
    elif args.command == "roc_pr":
        plot_roc_pr(args.predictions)
    elif args.command == "training_curves":
        plot_training_curves(args.history)
    elif args.command == "model_comparison":
        plot_model_comparison(args.final_results)
    elif args.command == "robustness":
        plot_robustness(args.robustness_json)
