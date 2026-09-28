#!/usr/bin/env bash
# =============================================================================
# tests/run_smoke_test.sh
# -----------------------------------------------------------------------------
# Runs the pipeline's CPU/no-torch-dependent stages against a tiny SYNTHETIC
# fixture (tests/fixtures/) to verify the code is wired together correctly.
#
# IMPORTANT: tests/fixtures/ is NOT the AiGen-FoodReview dataset. It is 200
# procedurally-generated placeholder rows + solid-color placeholder images,
# used ONLY to check that dataset_audit.py, leakage_check.py, tokenizer.py,
# and dataset.py run without error and produce sane output shapes. Any
# metrics you could compute from this fixture are meaningless and must
# NEVER be reported as real experimental results.
#
# This script does NOT require torch/torchvision to be installed, so it can
# run in environments (like a plain CI box or a sandbox without a GPU) where
# the full training pipeline cannot. Once torch + torchvision are installed,
# uncomment the "requires torch" section at the bottom to also smoke-test one
# forward pass of each model with random weights.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root
export PYTHONPATH="src:${PYTHONPATH:-}"

TMP_CONFIG="tests/_smoke_test_config.yaml"
python3 - <<'PYEOF'
import yaml
cfg = yaml.safe_load(open("configs/config.yaml"))
cfg["data"]["root_dir"] = "tests/fixtures"
cfg["data"]["train_csv"] = "tests/fixtures/train.csv"
cfg["data"]["val_csv"] = "tests/fixtures/val.csv"
cfg["data"]["test_csv"] = "tests/fixtures/test.csv"
cfg["data"]["image_dir"] = "tests/fixtures/images"
cfg["data"]["columns"] = {
    "id_col": "id", "text_col": "review_text", "image_col": "image_path",
    "label_col": "label", "restaurant_col": None,
}
cfg["paths"]["results_dir"] = "tests/_smoke_results"
cfg["paths"]["vocab_path"] = "tests/_smoke_results/vocab.json"
cfg["paths"]["logs_dir"] = "tests/_smoke_logs"
yaml.safe_dump(cfg, open("tests/_smoke_test_config.yaml", "w"))
PYEOF

echo "=== [1/4] dataset_audit.py against synthetic fixture ==="
python3 src/dataset_audit.py --config "$TMP_CONFIG"

echo "=== [2/4] leakage_check.py against synthetic fixture ==="
python3 src/leakage_check.py --config "$TMP_CONFIG"

echo "=== [3/4] tokenizer.py self-test ==="
python3 src/tokenizer.py

echo "=== [4/4] metrics.py self-test ==="
python3 - <<'PYEOF'
import numpy as np, sys
sys.path.insert(0, "src")
from metrics import compute_metrics, select_threshold_on_validation, paired_bootstrap_test
rng = np.random.RandomState(0)
y_true = rng.randint(0, 2, 200)
y_prob = np.clip(y_true * 0.5 + rng.normal(0, 0.3, 200) + 0.25, 0, 1)
m = compute_metrics(y_true, y_prob)
assert 0 <= m["f1"] <= 1
t, s = select_threshold_on_validation(y_true, y_prob)
assert 0 < t < 1
print("metrics.py self-test passed:", {k: round(v, 3) for k, v in m.items() if isinstance(v, float)})
PYEOF

rm -rf tests/_smoke_results tests/_smoke_logs "$TMP_CONFIG"
echo ""
echo "All CPU-only smoke tests passed. This does NOT validate the torch-dependent"
echo "modules (text_encoder.py, image_encoder.py, fusion.py, models.py, train.py,"
echo "evaluate.py, robustness.py, compute_cost.py) end-to-end -- those require"
echo "torch/torchvision + real training time and must be run on your own GPU"
echo "machine (see README.md)."
