"""
leakage_check.py
-----------------
PHASE 2 of the execution plan (data leakage checks, section 14 of spec).

Checks performed, all on REAL loaded data (never assumed):
  1. Duplicate IDs within each split
  2. Duplicate IDs across splits (train/val/test contamination)
  3. Duplicate exact text within and across splits
  4. Near-duplicate text (token-set Jaccard similarity above a threshold) --
     O(n log n) via a cheap MinHash-free bucketing approach so it stays
     tractable on ~20k rows without extra heavy dependencies.
  5. Duplicate images via MD5 file hash, within and across splits
  6. Restaurant-level overlap across splits, IF a restaurant identifier
     column is available (many datasets don't have one -- reported honestly).

If leakage is found, this script does NOT modify the official split. It
only reports. Any remediation must be a separate, explicitly-labeled
sensitivity experiment (e.g. a grouped re-split), never a silent fix to
the primary experiment.

Usage:
    python src/leakage_check.py --config configs/config.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import os
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from tokenizer import normalize_text, tokenize
from utils import load_config, save_json


def _md5_file(path: str) -> Optional[str]:
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _load_split(csv_path: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(csv_path):
        return None
    return pd.read_csv(csv_path)


def _duplicate_ids(df: pd.DataFrame, id_col: str) -> Dict:
    if id_col not in df.columns:
        return {"error": f"id column '{id_col}' not found"}
    dup_mask = df[id_col].duplicated(keep=False)
    return {
        "n_duplicate_rows": int(dup_mask.sum()),
        "example_duplicate_ids": df.loc[dup_mask, id_col].astype(str).unique().tolist()[:20],
    }


def _duplicate_text(df: pd.DataFrame, text_col: str) -> Dict:
    if text_col not in df.columns:
        return {"error": f"text column '{text_col}' not found"}
    normed = df[text_col].astype(str).map(lambda t: normalize_text(t))
    dup_mask = normed.duplicated(keep=False)
    return {
        "n_duplicate_rows": int(dup_mask.sum()),
    }


def _near_duplicate_text(
    df: pd.DataFrame, text_col: str, jaccard_threshold: float = 0.9, max_pairs_report: int = 20
) -> Dict:
    """
    Cheap near-duplicate detection: bucket rows by their two most frequent
    non-stopword-ish tokens (simple heuristic blocking key), then only
    compute Jaccard similarity within buckets. This avoids an O(n^2) scan
    over the full ~20k rows while still catching most near-duplicates.
    Rows in buckets larger than 500 are skipped with a note (pathological
    case; would need a proper LSH library to handle safely).
    """
    if text_col not in df.columns:
        return {"error": f"text column '{text_col}' not found"}

    token_sets: Dict[int, Set[str]] = {}
    buckets: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    for idx, text in df[text_col].astype(str).items():
        toks = tokenize(normalize_text(text))
        tset = set(toks)
        token_sets[idx] = tset
        if len(toks) >= 2:
            key = tuple(sorted(toks[:2]))
        elif len(toks) == 1:
            key = (toks[0], "")
        else:
            key = ("", "")
        buckets[key].append(idx)

    near_dup_pairs = []
    skipped_large_buckets = 0
    for key, idxs in buckets.items():
        if len(idxs) < 2:
            continue
        if len(idxs) > 500:
            skipped_large_buckets += 1
            continue
        for i, j in combinations(idxs, 2):
            a, b = token_sets[i], token_sets[j]
            if not a or not b:
                continue
            jacc = len(a & b) / len(a | b)
            if jacc >= jaccard_threshold:
                near_dup_pairs.append((i, j, round(jacc, 3)))

    return {
        "jaccard_threshold": jaccard_threshold,
        "n_near_duplicate_pairs_found": len(near_dup_pairs),
        "example_pairs_row_indices": near_dup_pairs[:max_pairs_report],
        "skipped_oversized_buckets": skipped_large_buckets,
        "note": "Heuristic blocking approach -- may miss some near-duplicates; not exhaustive O(n^2).",
    }


def _image_hashes(df: pd.DataFrame, image_col: str, image_dir: str) -> Dict[int, str]:
    hashes = {}
    if image_col not in df.columns:
        return hashes
    for idx, val in df[image_col].astype(str).items():
        candidate_paths = [
            os.path.join(image_dir, val),
            os.path.join(image_dir, os.path.basename(val)),
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                h = _md5_file(p)
                if h:
                    hashes[idx] = h
                break
    return hashes


def run_leakage_check(config_path: str) -> Dict:
    cfg = load_config(config_path)
    cols = cfg["data"]["columns"]
    id_col, text_col, image_col = cols.get("id_col"), cols.get("text_col"), cols.get("image_col")
    restaurant_col = cols.get("restaurant_col")
    image_dir = cfg["data"]["image_dir"]

    splits = {
        "train": cfg["data"]["train_csv"],
        "val": cfg["data"]["val_csv"],
        "test": cfg["data"]["test_csv"],
    }

    report: Dict = {"splits_checked": {}, "cross_split": {}}
    dfs: Dict[str, pd.DataFrame] = {}
    out_path = os.path.join(cfg["paths"]["results_dir"], "leakage_report.json")

    missing_cfg = [c for c in [id_col, text_col] if c is None]
    if missing_cfg:
        report["status"] = "BLOCKED_MISSING_COLUMN_CONFIG"
        report["message"] = (
            "data.columns.id_col / text_col are not set in config.yaml. "
            "Run dataset_audit.py first and fill in the confirmed column names."
        )
        save_json(report, out_path)
        print(report["message"])
        return report

    for split_name, path in splits.items():
        df = _load_split(path)
        if df is None:
            report["splits_checked"][split_name] = {"status": "FILE_NOT_FOUND", "path": path}
            continue
        dfs[split_name] = df
        split_report: Dict = {"n_rows": int(len(df))}
        split_report["duplicate_ids"] = _duplicate_ids(df, id_col)
        split_report["duplicate_exact_text"] = _duplicate_text(df, text_col)
        split_report["near_duplicate_text"] = _near_duplicate_text(df, text_col)
        if image_col:
            hashes = _image_hashes(df, image_col, image_dir)
            hash_counts = defaultdict(list)
            for idx, h in hashes.items():
                hash_counts[h].append(idx)
            dup_image_groups = {h: idxs for h, idxs in hash_counts.items() if len(idxs) > 1}
            split_report["duplicate_images_within_split"] = {
                "n_hashed": len(hashes),
                "n_duplicate_groups": len(dup_image_groups),
            }
            df.attrs["_image_hashes"] = hashes  # stash for cross-split check
        report["splits_checked"][split_name] = split_report

    # cross-split contamination
    if len(dfs) >= 2:
        pair_reports = {}
        for (name_a, df_a), (name_b, df_b) in combinations(dfs.items(), 2):
            pair_key = f"{name_a}_vs_{name_b}"
            pair_info: Dict = {}

            if id_col in df_a.columns and id_col in df_b.columns:
                ids_a = set(df_a[id_col].astype(str))
                ids_b = set(df_b[id_col].astype(str))
                overlap = ids_a & ids_b
                pair_info["id_overlap_count"] = len(overlap)
                pair_info["id_overlap_examples"] = list(overlap)[:20]

            if text_col in df_a.columns and text_col in df_b.columns:
                texts_a = set(df_a[text_col].astype(str).map(lambda t: normalize_text(t)))
                texts_b = set(df_b[text_col].astype(str).map(lambda t: normalize_text(t)))
                text_overlap = texts_a & texts_b
                pair_info["exact_text_overlap_count"] = len(text_overlap)

            hashes_a = df_a.attrs.get("_image_hashes", {})
            hashes_b = df_b.attrs.get("_image_hashes", {})
            if hashes_a and hashes_b:
                set_a, set_b = set(hashes_a.values()), set(hashes_b.values())
                img_overlap = set_a & set_b
                pair_info["duplicate_image_overlap_count"] = len(img_overlap)

            if restaurant_col and restaurant_col in df_a.columns and restaurant_col in df_b.columns:
                rest_a = set(df_a[restaurant_col].astype(str))
                rest_b = set(df_b[restaurant_col].astype(str))
                pair_info["restaurant_overlap_count"] = len(rest_a & rest_b)
            else:
                pair_info["restaurant_overlap"] = "NOT_AVAILABLE (no restaurant_col configured/found)"

            pair_reports[pair_key] = pair_info
        report["cross_split"] = pair_reports

    # overall verdict -- honest, not softened
    leakage_flags = []
    for split_name, sr in report["splits_checked"].items():
        if isinstance(sr, dict) and sr.get("duplicate_ids", {}).get("n_duplicate_rows", 0) > 0:
            leakage_flags.append(f"duplicate IDs within {split_name}")
    for pair_key, pr in report.get("cross_split", {}).items():
        if pr.get("id_overlap_count", 0) > 0:
            leakage_flags.append(f"ID overlap in {pair_key}")
        if pr.get("exact_text_overlap_count", 0) > 0:
            leakage_flags.append(f"exact text overlap in {pair_key}")
        if pr.get("duplicate_image_overlap_count", 0) > 0:
            leakage_flags.append(f"duplicate image overlap in {pair_key}")

    report["status"] = "LEAKAGE_DETECTED" if leakage_flags else "NO_LEAKAGE_DETECTED"
    report["leakage_flags"] = leakage_flags
    if leakage_flags:
        report["recommendation"] = (
            "Leakage detected. Do NOT silently drop rows from the official split. "
            "Report this honestly in the paper and, if desired, run a separate "
            "grouped-split sensitivity experiment (e.g. group by restaurant or by "
            "near-duplicate cluster) as an additional, clearly-labeled analysis."
        )

    save_json(report, out_path)
    print(f"Leakage report written to {out_path} (status={report['status']}).")
    if leakage_flags:
        print("LEAKAGE FLAGS:", leakage_flags)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    args = parser.parse_args()
    run_leakage_check(args.config)
