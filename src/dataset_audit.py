"""
dataset_audit.py
-----------------
PHASE 1-2 of the execution plan.

This script performs a REAL inspection of whatever is on disk under
`data.root_dir` -- it does NOT assume column names, file layout, or class
balance. It reports what it actually finds and writes
`results/dataset_audit.json`.

Run this BEFORE writing anything else into `configs/config.yaml`'s
`data.columns` block. The output tells you the true column names / paths
to fill in there.

Usage:
    python src/dataset_audit.py --config configs/config.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from utils import load_config, save_json

# Column-name candidates we heuristically check for -- suggestions only.
# The script reports these as CANDIDATES; it never silently commits to one
# without printing all options and requiring explicit confirmation in the
# config file.
ID_CANDIDATES = ["id", "review_id", "sample_id", "uid", "index"]
TEXT_CANDIDATES = ["text", "review", "review_text", "content", "body"]
IMAGE_CANDIDATES = ["image", "image_id", "image_path", "img", "img_path", "filename", "file_name"]
LABEL_CANDIDATES = ["label", "class", "target", "is_fake", "is_machine_generated", "y"]
RESTAURANT_CANDIDATES = ["restaurant", "restaurant_id", "business_id", "place_id"]


def _find_candidates(columns: List[str], candidates: List[str]) -> List[str]:
    cols_lower = {c.lower(): c for c in columns}
    hits = []
    for cand in candidates:
        for cl, orig in cols_lower.items():
            if cand == cl or cand in cl:
                hits.append(orig)
    # de-dup, preserve order
    seen = set()
    out = []
    for h in hits:
        if h not in seen:
            out.append(h)
            seen.add(h)
    return out


def discover_files(root_dir: str) -> Dict[str, Any]:
    root = Path(root_dir)
    if not root.exists():
        return {"root_exists": False, "root_dir": str(root)}

    csv_files = [str(p) for p in root.rglob("*.csv")]
    tsv_files = [str(p) for p in root.rglob("*.tsv")]
    json_files = [str(p) for p in root.rglob("*.json")]
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    image_files = [str(p) for p in root.rglob("*") if p.suffix.lower() in image_exts]
    image_dirs = sorted({str(p.parent) for p in root.rglob("*") if p.suffix.lower() in image_exts})

    return {
        "root_exists": True,
        "root_dir": str(root),
        "csv_files": csv_files,
        "tsv_files": tsv_files,
        "json_files": json_files,
        "num_images_found": len(image_files),
        "image_directories": image_dirs,
        "sample_image_files": image_files[:10],
    }


def audit_csv(path: str, image_dirs: List[str], nrows_sample: int = 5) -> Dict[str, Any]:
    df = pd.read_csv(path)
    columns = list(df.columns)

    id_cands = _find_candidates(columns, ID_CANDIDATES)
    text_cands = _find_candidates(columns, TEXT_CANDIDATES)
    image_cands = _find_candidates(columns, IMAGE_CANDIDATES)
    label_cands = _find_candidates(columns, LABEL_CANDIDATES)
    restaurant_cands = _find_candidates(columns, RESTAURANT_CANDIDATES)

    info: Dict[str, Any] = {
        "path": path,
        "n_rows": int(len(df)),
        "columns": columns,
        "dtypes": {c: str(df[c].dtype) for c in columns},
        "candidate_id_columns": id_cands,
        "candidate_text_columns": text_cands,
        "candidate_image_columns": image_cands,
        "candidate_label_columns": label_cands,
        "candidate_restaurant_columns": restaurant_cands,
        "sample_rows": df.head(nrows_sample).to_dict(orient="records"),
        "null_counts": {c: int(df[c].isna().sum()) for c in columns},
    }

    # class distribution, only if a plausible label column exists
    if label_cands:
        label_col = label_cands[0]
        try:
            info["label_value_counts"] = {
                str(k): int(v) for k, v in df[label_col].value_counts(dropna=False).items()
            }
        except Exception as e:
            info["label_value_counts_error"] = str(e)

    # duplicate ID check, only if a plausible id column exists
    if id_cands:
        id_col = id_cands[0]
        dup_count = int(df[id_col].duplicated().sum())
        info["duplicate_id_count"] = dup_count
        info["duplicate_id_column_used"] = id_col

    # duplicate exact text check
    if text_cands:
        text_col = text_cands[0]
        dup_text_count = int(df[text_col].astype(str).duplicated().sum())
        info["duplicate_exact_text_count"] = dup_text_count
        info["duplicate_text_column_used"] = text_col

    # image existence check, only if a plausible image column + known image dirs exist
    if image_cands and image_dirs:
        image_col = image_cands[0]
        existing_files = set()
        for d in image_dirs:
            for p in Path(d).iterdir():
                if p.is_file():
                    existing_files.add(p.name)
        missing = 0
        checked = 0
        for val in df[image_col].astype(str).tolist():
            checked += 1
            base = os.path.basename(val)
            # try exact name, and a couple of common extension variants
            candidates = {base, base + ".jpg", base + ".jpeg", base + ".png"}
            if not (candidates & existing_files):
                missing += 1
        info["image_column_used"] = image_col
        info["images_checked"] = checked
        info["images_missing"] = missing

    return info


def md5_of_file(path: str) -> Optional[str]:
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def run_audit(config_path: str) -> Dict[str, Any]:
    cfg = load_config(config_path)
    root_dir = cfg["data"]["root_dir"]
    out_path = os.path.join(cfg["paths"]["results_dir"], "dataset_audit.json")

    discovery = discover_files(root_dir)
    report: Dict[str, Any] = {"discovery": discovery, "csv_audits": {}}

    if not discovery.get("root_exists"):
        report["status"] = "NO_DATA_FOUND"
        report["message"] = (
            f"data.root_dir='{root_dir}' does not exist. Place the AiGen-FoodReview "
            f"dataset (CSV(s) + image folder) there and re-run this script."
        )
        save_json(report, out_path)
        print(report["message"])
        return report

    csv_candidates = discovery["csv_files"] + discovery["tsv_files"]
    if not csv_candidates:
        report["status"] = "NO_CSV_FOUND"
        report["message"] = f"No .csv/.tsv files found under {root_dir}."
        save_json(report, out_path)
        print(report["message"])
        return report

    image_dirs = discovery["image_directories"]
    for csv_path in csv_candidates:
        try:
            report["csv_audits"][csv_path] = audit_csv(csv_path, image_dirs)
        except Exception as e:
            report["csv_audits"][csv_path] = {"error": str(e)}

    report["status"] = "INSPECTED"
    report["note"] = (
        "Column names above are CANDIDATES only (heuristic name matching). "
        "Confirm the correct id/text/image/label columns manually and set them "
        "explicitly in configs/config.yaml under data.columns before training. "
        "Do not proceed on autodetected guesses alone."
    )
    save_json(report, out_path)
    print(f"Dataset audit written to {out_path} (status={report['status']}).")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    args = parser.parse_args()
    run_audit(args.config)
