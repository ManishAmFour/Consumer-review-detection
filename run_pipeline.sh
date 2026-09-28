#!/usr/bin/env bash
# =============================================================================
# run_pipeline.sh
# -----------------------------------------------------------------------------
# Runs the ENTIRE experiment pipeline (spec section 25, Phases 1-17) in order.
#
# PREREQUISITES (this script will not fabricate any of these for you):
#   1. The real AiGen-FoodReview dataset is placed under data/ (CSV(s) + an
#      images folder).
#   2. You have run Phase 1 manually first:
#         python src/dataset_audit.py --config configs/config.yaml
#      inspected results/dataset_audit.json, and filled in the CONFIRMED
#      column names under configs/config.yaml -> data.columns (id_col,
#      text_col, image_col, label_col). This script refuses to proceed if
#      those are still null.
#   3. pip install -r requirements.txt (needs a real PyTorch + torchvision;
#      GPU strongly recommended -- see README.md for expected runtimes).
#
# Usage:
#   bash run_pipeline.sh
#   bash run_pipeline.sh --skip-hparam-search   # use configs/config.yaml as-is
# =============================================================================
set -euo pipefail

CONFIG="configs/config.yaml"
export PYTHONPATH="src:${PYTHONPATH:-}"

SKIP_HPARAM_SEARCH=false
for arg in "$@"; do
  case "$arg" in
    --skip-hparam-search) SKIP_HPARAM_SEARCH=true ;;
  esac
done

echo "=============================================================="
echo "PHASE 1-2: Dataset audit + leakage check"
echo "=============================================================="
python3 src/dataset_audit.py --config "$CONFIG"

python3 - "$CONFIG" <<'PYEOF'
import sys, yaml
cfg = yaml.safe_load(open(sys.argv[1]))
cols = cfg["data"]["columns"]
required = ["id_col", "text_col", "image_col", "label_col"]
missing = [c for c in required if cols.get(c) is None]
if missing:
    print(f"\nERROR: configs/config.yaml is missing confirmed column names: {missing}")
    print("Open results/dataset_audit.json, confirm the real columns, fill them into")
    print("configs/config.yaml -> data.columns, then re-run this script.")
    sys.exit(1)
print("Column configuration confirmed:", cols)
PYEOF

python3 src/leakage_check.py --config "$CONFIG"
echo "Review results/leakage_report.json before continuing. Ctrl+C now if leakage was found and you want to stop."

echo "=============================================================="
echo "PHASE 6-7: Hyperparameter search (train+val only)"
echo "=============================================================="
if [ "$SKIP_HPARAM_SEARCH" = false ]; then
  python3 src/hparam_search.py --config "$CONFIG" --model_type gated
  echo "Review results/best_hparams.json and manually update configs/config.yaml if desired."
else
  echo "Skipped (--skip-hparam-search passed)."
fi

echo "=============================================================="
echo "PHASE 3-13: Train + evaluate all 5 models across all 3 seeds"
echo "=============================================================="
for MODEL in text_only image_only concat gated gated_finetuned; do
  echo "--- Seed experiments for model_type=$MODEL ---"
  python3 src/seed_experiments.py --config "$CONFIG" --model_type "$MODEL"
done

echo "=============================================================="
echo "PHASE 14: Robustness suite (multimodal models only, seed 42 checkpoints)"
echo "=============================================================="
for MODEL in concat gated gated_finetuned; do
  THRESH=$(python3 -c "
import json
d = json.load(open('results/eval_${MODEL}_seed42.json'))
print(d['validation_selected_threshold'])
")
  python3 src/robustness.py --config "$CONFIG" \
    --checkpoint "checkpoints/${MODEL}_seed42_best.pt" \
    --frozen_threshold "$THRESH"
done

echo "=============================================================="
echo "PHASE 15: Computational cost analysis"
echo "=============================================================="
python3 src/compute_cost.py --config "$CONFIG" --checkpoints \
  checkpoints/text_only_seed42_best.pt \
  checkpoints/image_only_seed42_best.pt \
  checkpoints/concat_seed42_best.pt \
  checkpoints/gated_seed42_best.pt \
  checkpoints/gated_finetuned_seed42_best.pt

echo "=============================================================="
echo "Error analysis + interpretability (gated model, seed 42)"
echo "=============================================================="
python3 src/error_analysis.py --config "$CONFIG" --predictions results/predictions_gated_seed42.csv
python3 src/interpretability.py --predictions results/predictions_gated_seed42.csv \
  --robustness_json results/robustness_gated.json

echo "=============================================================="
echo "PHASE 16: Generate all plots"
echo "=============================================================="
python3 src/plotting.py confusion_matrix --predictions results/predictions_gated_seed42.csv --threshold 0.5
python3 src/plotting.py roc_pr --predictions results/predictions_gated_seed42.csv
python3 src/plotting.py training_curves --history results/train_history_gated_seed42.json
python3 src/plotting.py robustness --robustness_json results/robustness_gated.json
# model_comparison.png needs final_results.csv, produced by the aggregation step below,
# so it is generated as part of Phase 17 instead.

echo "=============================================================="
echo "PHASE 17: Aggregate results, statistical comparison, research report"
echo "=============================================================="
python3 src/aggregate_results.py --config "$CONFIG"
python3 src/plotting.py model_comparison --final_results results/final_results.csv

echo "=============================================================="
echo "DONE. See research_report.md, results/, and plots/."
echo "=============================================================="
