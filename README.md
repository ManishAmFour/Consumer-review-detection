# Reliability-Gated Multimodal Fusion for Machine-Generated Restaurant Review Detection

Code accompanying: *"A Multimodal Bi-LSTM–ResNet-50 Framework with
Reliability-Gated Fusion for Detecting Machine-Generated Restaurant
Reviews."*

## What this repository is (and is not)

This is a **complete, runnable implementation** of the architecture,
baselines, ablations, robustness tests, and analysis pipeline described in
the paper spec. It was authored and code-reviewed in a sandboxed
environment with **no GPU, one CPU core, and no internet access** -- so it
could not itself download the AiGen-FoodReview dataset, install
torch/torchvision, or run real multi-epoch training. Concretely:

| Component | Status here |
|---|---|
| `dataset_audit.py`, `leakage_check.py`, `tokenizer.py`, `metrics.py` | **Executed and verified** against a synthetic fixture (`tests/fixtures/`) — see `tests/run_smoke_test.sh` |
| `text_encoder.py`, `image_encoder.py`, `fusion.py`, `models.py`, `train.py`, `evaluate.py`, `robustness.py`, `compute_cost.py` | Written to spec, syntax-checked (`python -m py_compile`), and manually verified line-by-line against the architecture spec. **Not executed** (no torch available in the authoring sandbox). Run `tests/test_forward_pass.py` first once you have torch installed. |
| Any experimental numbers (accuracy, F1, etc.) | **None are included anywhere in this repo.** Every results file, plot, and report is generated fresh from your own actual runs. |

**Do not treat anything in `results/` or `plots/` as populated -- those
directories are empty until you run the pipeline yourself.**

## Requirements

- Python 3.10+
- A CUDA GPU is strongly recommended. The spec's primary target is a
  Google Colab T4 instance; CPU fallback works but will be slow,
  especially for the ResNet-50 branches.
- `pip install -r requirements.txt`

## 1. Get the data in place

Place the AiGen-FoodReview CSV(s) and image folder under `data/`, e.g.:

```
data/
├── train.csv
├── val.csv
├── test.csv
└── images/
    ├── ...
```

(or a single CSV with a split column -- `dataset_audit.py` will find
whatever layout you actually have; it does not assume one.)

## 2. Run the dataset audit (mandatory first step)

```bash
python src/dataset_audit.py --config configs/config.yaml
```

Open `results/dataset_audit.json`. It lists every CSV found, their real
column names, candidate id/text/image/label columns, class distributions,
and missing-image counts. **Confirm** the real column names and fill them
into `configs/config.yaml` under `data.columns` -- the pipeline will refuse
to train until these are set explicitly (no silent guessing).

## 3. Run the leakage check (mandatory before training)

```bash
python src/leakage_check.py --config configs/config.yaml
```

Inspect `results/leakage_report.json`. If `status` is `LEAKAGE_DETECTED`,
read `leakage_flags` and decide how to report it in the paper -- the
official split is never silently modified by this codebase.

## 4. (Optional but recommended) hyperparameter search

```bash
python src/hparam_search.py --config configs/config.yaml --model_type gated
```

Uses train+val only (the test CSV is never read by this script). Review
`results/best_hparams.json` and manually copy the chosen values into
`configs/config.yaml` if you want to adopt them as the principal
configuration.

## 5. Run everything else

```bash
bash run_pipeline.sh
```

This runs, in order: baseline training (5 model types × 3 seeds each, with
early stopping on validation F1), the frozen validation-selected threshold
protocol, robustness experiments, computational-cost measurement, error
analysis, interpretability (gate) analysis, all required plots, and the
final `research_report.md`. It's a thin wrapper around the individual
scripts in `src/` -- read it to see (or copy) the exact commands, or run
each phase yourself for finer control:

```bash
python src/train.py --config configs/config.yaml --seed 42 --model_type gated
python src/evaluate.py --config configs/config.yaml --checkpoint checkpoints/gated_seed42_best.pt
python src/seed_experiments.py --config configs/config.yaml --model_type gated   # all 3 seeds
python src/robustness.py --config configs/config.yaml --checkpoint checkpoints/gated_seed42_best.pt --frozen_threshold 0.51
python src/compute_cost.py --config configs/config.yaml --checkpoints checkpoints/*_seed42_best.pt
python src/error_analysis.py --config configs/config.yaml --predictions results/predictions_gated_seed42.csv
python src/interpretability.py --predictions results/predictions_gated_seed42.csv --robustness_json results/robustness_gated.json
python src/aggregate_results.py --config configs/config.yaml
```

## Project structure

```
project/
├── configs/config.yaml       # single source of truth for every hyperparameter/path
├── data/                     # put the real dataset here (not included)
├── src/
│   ├── utils.py              # seeding, device/env detection, logging, param counting
│   ├── dataset_audit.py      # Phase 1-2: inspect real data, no assumed schema
│   ├── leakage_check.py      # Phase 2: duplicate/leakage checks, never modifies splits
│   ├── tokenizer.py          # train-only vocab, masked-mean-pool-ready padding/mask
│   ├── dataset.py            # PyTorch Dataset/DataLoader, lazy image loading
│   ├── text_encoder.py       # Embedding -> BiLSTM -> masked mean pool -> F_T
│   ├── image_encoder.py      # ResNet-50 -> GAP -> F_I, frozen or last-block-unfrozen
│   ├── fusion.py             # ConcatFusion and ReliabilityGatedFusion
│   ├── models.py             # assembles the 5 required models
│   ├── metrics.py            # all required metrics + paired bootstrap CI
│   ├── train.py              # training loop, early stopping, checkpointing, AMP
│   ├── evaluate.py           # frozen-threshold test protocol (val selects, test scores once)
│   ├── hparam_search.py      # compact grid search, train+val only
│   ├── seed_experiments.py   # runs 3 seeds, aggregates mean+-SD
│   ├── robustness.py         # modality removal / image degradation / text perturbation
│   ├── compute_cost.py       # real parameter counts, GPU memory, latency, throughput
│   ├── error_analysis.py     # representative TP/TN/FP/FN extraction + categorization
│   ├── interpretability.py   # gate-value distribution analysis (descriptive only)
│   ├── plotting.py           # every required figure, from real saved results only
│   └── aggregate_results.py  # final_results.csv, statistical comparison, research_report.md
├── tests/
│   ├── fixtures/              # tiny SYNTHETIC data for pipeline smoke-testing (not real data)
│   ├── run_smoke_test.sh      # torch-free correctness check (audit/leakage/tokenizer/metrics)
│   └── test_forward_pass.py   # torch-dependent shape/backward-pass check (run once torch is installed)
├── run_pipeline.sh
├── requirements.txt
└── README.md
```

`experiments/`, `checkpoints/`, `results/`, `plots/`, `logs/` start empty
and are populated by the scripts above.

## Design decisions worth knowing about

- **Vocabulary is fit only on the training split** (`train.py` calls
  `Tokenizer.fit()` on the train CSV's text column exclusively).
- **Threshold selection never touches the test set.** `evaluate.py` scans
  thresholds on validation predictions, freezes the winner, then scores
  the test set exactly once at both 0.50 and the frozen threshold.
- **Hyperparameter search never loads the test CSV at all** (structural
  guarantee, not just "doesn't score it" -- see `hparam_search.py`).
- **Model 4 and Model 5 (gated / gated_finetuned) are the same class**
  (`GatedFusionModel`) with only the image encoder's frozen/unfrozen
  configuration differing, so the fusion mechanism is provably identical
  between the two ablation rows and the fine-tuning effect (RQ3) is
  isolated cleanly.
- **The reliability gate is never treated as a causal explanation**
  anywhere in the codebase (see the docstring in `fusion.py` and the
  disclaimer field in every `interpretability.py` output) -- only
  descriptive statistics (mean gate value per class, correlation with
  correctness) and empirical robustness deltas are reported.
- **Statistical comparison** (Concat vs Gated) uses a paired bootstrap over
  the *same* test predictions (`aggregate_results.py`), not independent
  bootstraps, since the two models are scored on identical test rows.
- **If leakage is found, or if gated fusion loses to concatenation, or if
  fine-tuning hurts performance, the codebase reports it as-is.** Nothing
  in `aggregate_results.py` or `research_report.md` generation special-
  cases a "good" outcome; `research_report.md` prints `NOT YET RUN` for
  any stage you haven't executed rather than inventing a number.

## A note on runtime expectations

With the full ~20k-sample dataset on a T4 GPU, expect (very roughly, and
you should measure your own real numbers with `compute_cost.py` rather
than trusting this estimate): a few minutes/epoch for the text-only model,
tens of seconds to a couple of minutes/epoch for the multimodal models
depending on image I/O, and correspondingly longer for the 3-seed x
5-model x (up to 30 epochs with early stopping) full sweep -- budget
several hours of GPU time for the complete `run_pipeline.sh`, not minutes.
#   C o n s u m e r - f a k e - r e v i e w - d e t e c t i o n  
 #   C o n s u m e r - f a k e - r e v i e w - d e t e c t i o n  
 