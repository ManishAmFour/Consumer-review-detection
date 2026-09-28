"""
image_encoder.py
-----------------
Image branch: ResNet-50 (ImageNet pretrained) with the classification head
removed, Global Average Pooling, then a trainable 2048 -> common_dim
projection (F_I).

Two modes, matching the spec:
  - PRIMARY:   freeze_backbone=True  -> entire ResNet-50 frozen
  - SECONDARY: unfreeze_last_block=True -> only `layer4` (the final
               residual block) is unfrozen for fine-tuning at a lower LR;
               everything before it stays frozen.
"""
from __future__ import annotations

import torch
import torch.nn as nn
from torchvision.models import ResNet50_Weights, resnet50


class ResNet50ImageEncoder(nn.Module):
    def __init__(
        self,
        common_dim: int = 256,
        pretrained: bool = True,
        freeze_backbone: bool = True,
        unfreeze_last_block: bool = False,
        dropout: float = 0.3,
    ):
        super().__init__()
        weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        backbone = resnet50(weights=weights)

        # Remove classification head; keep everything up to (and including)
        # the global average pool, which torchvision's resnet50 already
        # exposes as `.avgpool` (outputs (B, 2048, 1, 1)).
        self.stem = nn.Sequential(
            backbone.conv1,
            backbone.bn1,
            backbone.relu,
            backbone.maxpool,
        )
        self.layer1 = backbone.layer1
        self.layer2 = backbone.layer2
        self.layer3 = backbone.layer3
        self.layer4 = backbone.layer4  # final residual block
        self.avgpool = backbone.avgpool  # nn.AdaptiveAvgPool2d((1, 1))

        self.feature_dim = 2048
        self.projection = nn.Sequential(
            nn.Linear(self.feature_dim, common_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        self.set_trainable_mode(freeze_backbone=freeze_backbone, unfreeze_last_block=unfreeze_last_block)

    def set_trainable_mode(self, freeze_backbone: bool, unfreeze_last_block: bool) -> None:
        """
        Explicit, inspectable control over which backbone parameters get
        gradients. Called once at construction; can be called again if an
        experiment needs to change modes (e.g. moving from PRIMARY to
        SECONDARY configuration) -- always re-verify with count_parameters
        after calling this.
        """
        all_blocks = [self.stem, self.layer1, self.layer2, self.layer3, self.layer4]
        for block in all_blocks:
            for p in block.parameters():
                p.requires_grad = not freeze_backbone

        if freeze_backbone and unfreeze_last_block:
            for p in self.layer4.parameters():
                p.requires_grad = True

        # Projection head is always trainable regardless of backbone mode.
        for p in self.projection.parameters():
            p.requires_grad = True

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        """
        images: (B, 3, 224, 224)
        returns F_I: (B, common_dim)
        """
        x = self.stem(images)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)  # (B, 2048, 1, 1)
        x = torch.flatten(x, 1)  # (B, 2048)
        f_i = self.projection(x)  # (B, common_dim)
        return f_i

    def finetune_parameter_groups(self, lr_new: float, lr_finetune: float):
        """
        Returns optimizer param groups so that the (possibly unfrozen)
        layer4 gets a distinct, lower learning rate from the freshly
        initialized projection head, per the spec's requirement for
        separate LRs for new vs. fine-tuned layers.
        """
        groups = [{"params": self.projection.parameters(), "lr": lr_new}]
        finetune_params = [p for p in self.layer4.parameters() if p.requires_grad]
        if finetune_params:
            groups.append({"params": finetune_params, "lr": lr_finetune})
        return groups
