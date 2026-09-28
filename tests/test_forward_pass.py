"""
tests/test_forward_pass.py
---------------------------
OPTIONAL extra smoke test -- requires torch + torchvision to be installed.
Not run automatically by run_smoke_test.sh (which is torch-free by design
so it works in this authoring environment). Run this yourself once you have
torch available, BEFORE committing to a full multi-hour training run, to
catch shape/dtype bugs cheaply:

    pip install -r requirements.txt
    python tests/test_forward_pass.py

It builds each of the 5 models from src/models.py with a small random
vocab size, feeds them one random batch (no real data needed), and checks
the output logit shape is correct and that a backward pass runs without
error. It does NOT check numerical correctness of learned behavior --
only that every tensor shape lines up end-to-end.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import torch  # noqa: E402
import yaml  # noqa: E402

from models import build_model  # noqa: E402


def make_cfg():
    with open(os.path.join(os.path.dirname(__file__), "..", "configs", "config.yaml")) as f:
        return yaml.safe_load(f)


def make_dummy_batch(cfg, batch_size=4, vocab_size=50):
    max_len = cfg["text"]["max_seq_len"]
    resize = cfg["image"]["resize"]
    return {
        "text_ids": torch.randint(0, vocab_size, (batch_size, max_len)),
        "text_mask": torch.ones(batch_size, max_len, dtype=torch.bool),
        "image": torch.randn(batch_size, 3, resize, resize),
        "label": torch.randint(0, 2, (batch_size,), dtype=torch.float32),
    }


def check_model(model_type: str, cfg: dict, vocab_size: int = 50, batch_size: int = 4):
    print(f"--- {model_type} ---")
    model = build_model(model_type, vocab_size, cfg)
    batch = make_dummy_batch(cfg, batch_size, vocab_size)
    out = model(batch)
    logit = out["logit"]
    assert logit.shape == (batch_size,), f"Expected shape ({batch_size},), got {logit.shape}"

    loss = torch.nn.functional.binary_cross_entropy_with_logits(logit, batch["label"])
    loss.backward()

    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    print(f"  logit shape OK: {tuple(logit.shape)}")
    print(f"  backward pass OK, loss={loss.item():.4f}")
    print(f"  trainable={n_trainable:,} / total={n_total:,}")
    if "gate" in out:
        assert out["gate"].shape == (batch_size, cfg["model"]["common_dim"])
        print(f"  gate shape OK: {tuple(out['gate'].shape)}, mean={out['gate'].mean().item():.3f}")


def main():
    cfg = make_cfg()
    # Note: uses pretrained=True by default (downloads ImageNet weights on first
    # run, requires internet). Set cfg["model"]["image"]["pretrained"]=False here
    # if you want a fully offline shape-only check.
    for model_type in ["text_only", "image_only", "concat", "gated", "gated_finetuned"]:
        trial_cfg = cfg.copy()
        trial_cfg["model"] = {**cfg["model"], "image": {**cfg["model"]["image"]}}
        if model_type == "gated_finetuned":
            trial_cfg["model"]["image"]["unfreeze_last_block"] = True
        check_model(model_type, trial_cfg)
    print("\nAll forward/backward shape checks passed.")


if __name__ == "__main__":
    main()
