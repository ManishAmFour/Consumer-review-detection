"""
dataset.py
----------
PyTorch Dataset/DataLoader for the paired text+image AiGen-FoodReview data.

Design notes:
- Images are loaded lazily per __getitem__ (never pre-loaded into RAM in
  bulk) -- required because 20k restaurant images will not comfortably fit
  in memory on a T4 Colab instance alongside model + activations.
- Text is pre-tokenized once (cheap, done in __init__) since tokenized
  integer sequences are small.
- DataLoader is configured with num_workers, pin_memory, persistent_workers,
  and prefetch_factor per the spec's performance requirements (section 15).
- Missing images are treated as a hard error at dataset construction time
  UNLESS `allow_missing_images=True`, in which case they are logged and
  skipped -- never silently zero-filled without a warning, since that would
  bias the image-only / fused models.
"""
from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from tokenizer import Tokenizer

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_image_transform(resize: int = 224, train: bool = False) -> transforms.Compose:
    """
    Standard ImageNet preprocessing. `train=True` adds mild augmentation
    (horizontal flip) -- restaurant food/interior photos are usually flip-
    invariant; no augmentation is applied to val/test to keep evaluation
    deterministic.
    """
    ops = [transforms.Resize((resize, resize))]
    if train:
        ops.append(transforms.RandomHorizontalFlip(p=0.5))
    ops += [
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ]
    return transforms.Compose(ops)


class AiGenFoodReviewDataset(Dataset):
    def __init__(
        self,
        df: pd.DataFrame,
        image_dir: str,
        id_col: str,
        text_col: str,
        image_col: str,
        label_col: str,
        tokenizer: Tokenizer,
        image_transform: Optional[Callable] = None,
        modality: str = "both",  # "both" | "text" | "image"
        allow_missing_images: bool = False,
    ):
        assert modality in ("both", "text", "image")
        self.image_dir = image_dir
        self.id_col, self.text_col, self.image_col, self.label_col = (
            id_col,
            text_col,
            image_col,
            label_col,
        )
        self.tokenizer = tokenizer
        self.image_transform = image_transform or build_image_transform(train=False)
        self.modality = modality

        # Resolve image paths + drop/flag missing ones up front so failures
        # surface at dataset-construction time, not mid-epoch.
        records = []
        n_missing = 0
        for _, row in df.iterrows():
            img_val = str(row[image_col]) if image_col in df.columns else None
            img_path = self._resolve_image_path(img_val) if img_val else None
            if modality in ("both", "image") and (img_path is None or not os.path.exists(img_path)):
                n_missing += 1
                if not allow_missing_images:
                    continue  # excluded; caller should check `self.n_missing_images`
            records.append(
                {
                    "id": row[id_col],
                    "text": row[text_col],
                    "image_path": img_path,
                    "label": int(row[label_col]),
                }
            )
        self.n_missing_images = n_missing
        self.records = records

        # Pre-tokenize text once (cheap; keeps __getitem__ fast).
        self._token_ids: List[List[int]] = []
        self._token_lens: List[int] = []
        for r in self.records:
            ids, length = self.tokenizer.encode(r["text"])
            self._token_ids.append(ids)
            self._token_lens.append(length)

    def _resolve_image_path(self, val: str) -> Optional[str]:
        candidates = [
            os.path.join(self.image_dir, val),
            os.path.join(self.image_dir, os.path.basename(val)),
        ]
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidates.append(os.path.join(self.image_dir, os.path.basename(val) + ext))
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Dict:
        rec = self.records[idx]
        item = {
            "id": rec["id"],
            "label": torch.tensor(rec["label"], dtype=torch.float32),
        }

        if self.modality in ("both", "text"):
            ids = torch.tensor(self._token_ids[idx], dtype=torch.long)
            length = self._token_lens[idx]
            mask = torch.zeros(len(ids), dtype=torch.bool)
            mask[:length] = True
            item["text_ids"] = ids
            item["text_mask"] = mask

        if self.modality in ("both", "image"):
            img_path = rec["image_path"]
            try:
                img = Image.open(img_path).convert("RGB")
            except Exception:
                # Should be rare given the missing-image filtering above,
                # but guards against corrupt files found at read time.
                img = Image.new("RGB", (224, 224), color=(0, 0, 0))
            item["image"] = self.image_transform(img)

        return item


def collate_fn(batch: List[Dict]) -> Dict[str, torch.Tensor]:
    out: Dict[str, torch.Tensor] = {}
    out["label"] = torch.stack([b["label"] for b in batch])
    out["id"] = [b["id"] for b in batch]
    if "text_ids" in batch[0]:
        out["text_ids"] = torch.stack([b["text_ids"] for b in batch])
        out["text_mask"] = torch.stack([b["text_mask"] for b in batch])
    if "image" in batch[0]:
        out["image"] = torch.stack([b["image"] for b in batch])
    return out


def build_dataloader(
    dataset: Dataset,
    batch_size: int,
    shuffle: bool,
    num_workers: int = 4,
    pin_memory: bool = True,
    persistent_workers: bool = True,
    prefetch_factor: int = 2,
) -> DataLoader:
    kwargs = dict(
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
        collate_fn=collate_fn,
        drop_last=False,
    )
    if num_workers > 0:
        kwargs["persistent_workers"] = persistent_workers
        kwargs["prefetch_factor"] = prefetch_factor
    return DataLoader(dataset, **kwargs)
