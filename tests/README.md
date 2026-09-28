# tests/

`fixtures/` contains a tiny **synthetic** dataset (200 rows: solid-color
placeholder JPEGs + templated sentences, half labeled 0 / half labeled 1)
used only to verify the pipeline's code is wired together correctly:

- Column auto-detection in `dataset_audit.py`
- Duplicate/leakage detection logic in `leakage_check.py`
- Tokenizer + masked-mean-pooling shape handling
- `metrics.py` computations

**This is NOT the AiGen-FoodReview dataset, and no number produced from it
means anything about model quality.** Do not copy any metric computed
against `tests/fixtures/` into the paper.

Run it with:

```bash
bash tests/run_smoke_test.sh
```

This only exercises code paths that do not require `torch`/`torchvision`
(dataset audit, leakage check, tokenizer, metrics), so it can run anywhere,
including machines without a GPU or without deep learning libraries
installed. It does **not** validate `text_encoder.py`, `image_encoder.py`,
`fusion.py`, `models.py`, `train.py`, `evaluate.py`, `robustness.py`, or
`compute_cost.py` end-to-end -- those require a real `torch` install and
were verified by careful code review + `python -m py_compile`, not by
execution, in the environment this codebase was authored in (no GPU, no
internet access to install torch). Once you have torch/torchvision
installed, you can extend this script to instantiate each model in
`src/models.py` with the fixture's vocab size and run one forward pass as
an additional cheap correctness check before committing to a full,
multi-hour training run.
