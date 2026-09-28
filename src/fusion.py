"""
fusion.py
---------
Two fusion mechanisms operating on F_T, F_I in R^256:

1. ConcatFusion (MODEL 3 baseline):
       F = Linear([F_T ; F_I])   , 512 -> 256

2. ReliabilityGatedFusion (the paper's proposed contribution, MODEL 4/5):
       g = sigmoid(W_g [F_T ; F_I] + b_g),   g in (0,1)^256
       F = g * F_T + (1 - g) * F_I

   IMPORTANT (per spec section 4 and 22): the gate is a learned
   representation-weighting mechanism only. Nothing in this codebase
   should be written or reported as though gate values are causal
   explanations of the model's decision -- they are analyzed downstream
   (interpretability.py) purely as descriptive statistics (e.g. mean gate
   value per class), never as attributions of "why".
"""
from __future__ import annotations

from typing import Tuple

import torch
import torch.nn as nn


class ConcatFusion(nn.Module):
    def __init__(self, common_dim: int = 256, dropout: float = 0.3):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(common_dim * 2, common_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

    def forward(self, f_t: torch.Tensor, f_i: torch.Tensor) -> torch.Tensor:
        concat = torch.cat([f_t, f_i], dim=-1)  # (B, 512)
        return self.proj(concat)  # (B, 256)


class ReliabilityGatedFusion(nn.Module):
    def __init__(self, common_dim: int = 256):
        super().__init__()
        self.gate = nn.Linear(common_dim * 2, common_dim)  # W_g: 512 -> 256

    def forward(self, f_t: torch.Tensor, f_i: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        concat = torch.cat([f_t, f_i], dim=-1)  # (B, 512)
        g = torch.sigmoid(self.gate(concat))  # (B, 256), g in (0,1)
        fused = g * f_t + (1.0 - g) * f_i  # (B, 256)
        return fused, g  # gate returned for logging/interpretability, never used as loss target
