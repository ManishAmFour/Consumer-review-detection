"""
utils.py
--------
Shared utilities: reproducible seeding, device detection/reporting,
config loading, and lightweight logging helpers.

Nothing in this file fabricates or estimates anything -- it only reports
what is actually true about the running environment.
"""
from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import yaml


# ----------------------------------------------------------------------------
# Config loading
# ----------------------------------------------------------------------------
def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def save_json(obj: Any, path: str) -> None:
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


def load_json(path: str) -> Any:
    with open(path, "r") as f:
        return json.load(f)


# ----------------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------------
def set_seed(seed: int, deterministic_torch: bool = True) -> None:
    """
    Seed python, numpy, and torch (if installed). Called at the start of
    every training run. `deterministic_torch=True` trades a little speed
    for reproducibility -- appropriate here since the paper requires
    seed-level reproducibility.
    """
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if deterministic_torch:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


# ----------------------------------------------------------------------------
# Device / environment reporting
# ----------------------------------------------------------------------------
@dataclass
class EnvironmentReport:
    device: str
    gpu_name: Optional[str]
    gpu_total_memory_gb: Optional[float]
    torch_version: Optional[str]
    torchvision_version: Optional[str]
    cuda_version: Optional[str]
    cpu_count: int
    python_version: str


def detect_environment(print_report: bool = True) -> EnvironmentReport:
    """
    Detects cuda/cpu, GPU name/memory, torch/torchvision/cuda versions.
    This is a REAL runtime check -- it never assumes a GPU is present.
    """
    cpu_count = os.cpu_count() or 1
    py_version = sys.version.split()[0]

    torch_version = None
    torchvision_version = None
    cuda_version = None
    device = "cpu"
    gpu_name = None
    gpu_mem_gb = None

    try:
        import torch

        torch_version = torch.__version__
        if torch.cuda.is_available():
            device = "cuda"
            cuda_version = torch.version.cuda
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    except ImportError:
        pass

    try:
        import torchvision

        torchvision_version = torchvision.__version__
    except ImportError:
        pass

    report = EnvironmentReport(
        device=device,
        gpu_name=gpu_name,
        gpu_total_memory_gb=round(gpu_mem_gb, 2) if gpu_mem_gb else None,
        torch_version=torch_version,
        torchvision_version=torchvision_version,
        cuda_version=cuda_version,
        cpu_count=cpu_count,
        python_version=py_version,
    )

    if print_report:
        print("=" * 60)
        print("ENVIRONMENT REPORT")
        print("=" * 60)
        print(f"Device            : {report.device}")
        print(f"GPU name          : {report.gpu_name}")
        print(f"GPU total memory  : {report.gpu_total_memory_gb} GB")
        print(f"PyTorch version   : {report.torch_version}")
        print(f"torchvision vers. : {report.torchvision_version}")
        print(f"CUDA version      : {report.cuda_version}")
        print(f"CPU count         : {report.cpu_count}")
        print(f"Python version    : {report.python_version}")
        print("=" * 60)

    return report


# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
def get_logger(name: str, log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger  # avoid duplicate handlers on repeated calls

    fmt = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(os.path.join(log_dir, f"{name}.log"))
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


class Timer:
    """Simple context-manager timer used for real (not estimated) timing measurements."""

    def __init__(self):
        self.elapsed = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self._start


def count_parameters(model) -> Dict[str, int]:
    """Returns REAL trainable / frozen / total parameter counts for a torch.nn.Module."""
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    frozen = total - trainable
    return {"trainable_params": trainable, "frozen_params": frozen, "total_params": total}
