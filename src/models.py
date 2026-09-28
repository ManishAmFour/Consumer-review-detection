"""
models.py
---------
Assembles the five required models (spec section 5):

  MODEL 1: TextOnlyModel               (Bi-LSTM only)
  MODEL 2: ImageOnlyModel              (ResNet-50 only, frozen backbone)
  MODEL 3: ConcatFusionModel           (Bi-LSTM + ResNet-50, concat fusion)
  MODEL 4: GatedFusionModel            (Bi-LSTM + ResNet-50, reliability gate, frozen backbone)
  MODEL 5: GatedFusionModel            (same as 4, but image_encoder built with
                                         unfreeze_last_block=True -- this is a
                                         *configuration* of GatedFusionModel,
                                         not a separate class, so the fusion
                                         mechanism is provably identical
                                         between MODEL 4 and MODEL 5)

All models share the same classifier head shape: common_dim -> hidden_dim
-> ReLU -> Dropout -> 1 (logit). BCEWithLogitsLoss is used during training
(sigmoid applied only at inference/metric time) for numerical stability.
"""
from __future__ import annotations

from typing import Dict, Optional

import torch
import torch.nn as nn

from fusion import ConcatFusion, ReliabilityGatedFusion
from image_encoder import ResNet50ImageEncoder
from text_encoder import BiLSTMTextEncoder


class ClassifierHead(nn.Module):
    def __init__(self, in_dim: int = 256, hidden_dim: int = 128, dropout: float = 0.4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)  # (B,) raw logit


class TextOnlyModel(nn.Module):
    """MODEL 1."""

    def __init__(self, vocab_size: int, cfg: dict):
        super().__init__()
        m = cfg["model"]
        self.text_encoder = BiLSTMTextEncoder(
            vocab_size=vocab_size,
            embedding_dim=m["text"]["embedding_dim"],
            lstm_hidden=m["text"]["lstm_hidden"],
            lstm_layers=m["text"]["lstm_layers"],
            common_dim=m["common_dim"],
            dropout=m["classifier"]["dropout"],
        )
        self.classifier = ClassifierHead(
            in_dim=m["common_dim"], hidden_dim=m["classifier"]["hidden_dim"], dropout=m["classifier"]["dropout"]
        )

    def forward(self, batch: Dict) -> Dict[str, torch.Tensor]:
        f_t = self.text_encoder(batch["text_ids"], batch["text_mask"])
        logit = self.classifier(f_t)
        return {"logit": logit}


class ImageOnlyModel(nn.Module):
    """MODEL 2."""

    def __init__(self, cfg: dict):
        super().__init__()
        m = cfg["model"]
        self.image_encoder = ResNet50ImageEncoder(
            common_dim=m["common_dim"],
            pretrained=m["image"]["pretrained"],
            freeze_backbone=m["image"]["freeze_backbone"],
            unfreeze_last_block=m["image"]["unfreeze_last_block"],
            dropout=m["classifier"]["dropout"],
        )
        self.classifier = ClassifierHead(
            in_dim=m["common_dim"], hidden_dim=m["classifier"]["hidden_dim"], dropout=m["classifier"]["dropout"]
        )

    def forward(self, batch: Dict) -> Dict[str, torch.Tensor]:
        f_i = self.image_encoder(batch["image"])
        logit = self.classifier(f_i)
        return {"logit": logit}


class ConcatFusionModel(nn.Module):
    """MODEL 3."""

    def __init__(self, vocab_size: int, cfg: dict):
        super().__init__()
        m = cfg["model"]
        self.text_encoder = BiLSTMTextEncoder(
            vocab_size=vocab_size,
            embedding_dim=m["text"]["embedding_dim"],
            lstm_hidden=m["text"]["lstm_hidden"],
            lstm_layers=m["text"]["lstm_layers"],
            common_dim=m["common_dim"],
            dropout=m["classifier"]["dropout"],
        )
        self.image_encoder = ResNet50ImageEncoder(
            common_dim=m["common_dim"],
            pretrained=m["image"]["pretrained"],
            freeze_backbone=m["image"]["freeze_backbone"],
            unfreeze_last_block=m["image"]["unfreeze_last_block"],
            dropout=m["classifier"]["dropout"],
        )
        self.fusion = ConcatFusion(common_dim=m["common_dim"], dropout=m["classifier"]["dropout"])
        self.classifier = ClassifierHead(
            in_dim=m["common_dim"], hidden_dim=m["classifier"]["hidden_dim"], dropout=m["classifier"]["dropout"]
        )

    def forward(self, batch: Dict) -> Dict[str, torch.Tensor]:
        f_t = self.text_encoder(batch["text_ids"], batch["text_mask"])
        f_i = self.image_encoder(batch["image"])
        fused = self.fusion(f_t, f_i)
        logit = self.classifier(fused)
        return {"logit": logit, "f_t": f_t, "f_i": f_i}


class GatedFusionModel(nn.Module):
    """
    MODEL 4 (freeze_backbone=True in cfg) and MODEL 5 (unfreeze_last_block=True
    in cfg) are both instances of this same class -- the only difference is
    the image_encoder's trainable-parameter configuration, controlled
    entirely by `cfg['model']['image']`. This guarantees the fusion
    mechanism itself is byte-for-byte identical between the two ablation
    rows, isolating the fine-tuning effect (RQ3) cleanly.
    """

    def __init__(self, vocab_size: int, cfg: dict):
        super().__init__()
        m = cfg["model"]
        self.text_encoder = BiLSTMTextEncoder(
            vocab_size=vocab_size,
            embedding_dim=m["text"]["embedding_dim"],
            lstm_hidden=m["text"]["lstm_hidden"],
            lstm_layers=m["text"]["lstm_layers"],
            common_dim=m["common_dim"],
            dropout=m["classifier"]["dropout"],
        )
        self.image_encoder = ResNet50ImageEncoder(
            common_dim=m["common_dim"],
            pretrained=m["image"]["pretrained"],
            freeze_backbone=m["image"]["freeze_backbone"],
            unfreeze_last_block=m["image"]["unfreeze_last_block"],
            dropout=m["classifier"]["dropout"],
        )
        self.fusion = ReliabilityGatedFusion(common_dim=m["common_dim"])
        self.classifier = ClassifierHead(
            in_dim=m["common_dim"], hidden_dim=m["classifier"]["hidden_dim"], dropout=m["classifier"]["dropout"]
        )

    def forward(self, batch: Dict) -> Dict[str, torch.Tensor]:
        f_t = self.text_encoder(batch["text_ids"], batch["text_mask"])
        f_i = self.image_encoder(batch["image"])
        fused, gate = self.fusion(f_t, f_i)
        logit = self.classifier(fused)
        return {"logit": logit, "f_t": f_t, "f_i": f_i, "gate": gate}


def build_model(model_type: str, vocab_size: Optional[int], cfg: dict) -> nn.Module:
    """
    model_type in {"text_only", "image_only", "concat", "gated", "gated_finetuned"}.
    "gated_finetuned" is identical to "gated" except the caller must have
    set cfg['model']['image']['unfreeze_last_block']=True beforehand.
    """
    if model_type == "text_only":
        return TextOnlyModel(vocab_size, cfg)
    elif model_type == "image_only":
        return ImageOnlyModel(cfg)
    elif model_type == "concat":
        return ConcatFusionModel(vocab_size, cfg)
    elif model_type in ("gated", "gated_finetuned"):
        return GatedFusionModel(vocab_size, cfg)
    else:
        raise ValueError(f"Unknown model_type: {model_type}")
