"""
text_encoder.py
----------------
Text branch: Embedding -> Bidirectional LSTM -> masked mean pooling ->
trainable projection to the common representation space (F_T).
"""
from __future__ import annotations

import torch
import torch.nn as nn


class BiLSTMTextEncoder(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 128,
        lstm_hidden: int = 128,
        lstm_layers: int = 1,
        common_dim: int = 256,
        dropout: float = 0.3,
        pad_idx: int = 0,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=pad_idx)
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
        )
        self.lstm_out_dim = lstm_hidden * 2  # bidirectional -> 256 when lstm_hidden=128
        self.projection = nn.Sequential(
            nn.Linear(self.lstm_out_dim, common_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

    def masked_mean_pool(self, lstm_out: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """
        lstm_out: (B, T, H)  mask: (B, T) bool, True = real token
        Masked mean over the time dimension -- avoids diluting the
        representation with <pad> positions, and avoids relying solely on
        the (potentially noisy) final hidden state.
        """
        mask_f = mask.unsqueeze(-1).float()  # (B, T, 1)
        summed = (lstm_out * mask_f).sum(dim=1)  # (B, H)
        counts = mask_f.sum(dim=1).clamp(min=1e-6)  # (B, 1) avoid div-by-zero for empty text
        return summed / counts

    def forward(self, text_ids: torch.Tensor, text_mask: torch.Tensor) -> torch.Tensor:
        """
        text_ids: (B, T) long
        text_mask: (B, T) bool
        returns F_T: (B, common_dim)
        """
        embedded = self.embedding(text_ids)  # (B, T, E)
        lstm_out, _ = self.lstm(embedded)  # (B, T, 2*H)
        pooled = self.masked_mean_pool(lstm_out, text_mask)  # (B, 2*H)
        f_t = self.projection(pooled)  # (B, common_dim)
        return f_t
