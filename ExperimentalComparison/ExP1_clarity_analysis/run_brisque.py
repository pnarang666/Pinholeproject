"""
BRISQUE (no-reference image quality) scoring of ExP1 pinhole photos.
Lower score = better perceptual quality/less distortion; higher = worse.
Model: opencv_contrib brisque_model_live.yml / brisque_range_live.yml.

DNG->TIFF via sips (scratch, deleted after read) -> OpenCV 16-bit read ->
percentile-stretch to 8-bit (BRISQUE model trained on 8-bit natural images)
-> cv2.quality.QualityBRISQUE_compute().

Outputs (written to both OUT_DIRS): brisque_scores.csv, brisque_scores.xlsx
"""
import os
import subprocess
import csv

import numpy as np
import cv2
import pandas as pd

ROOT = "/Users/parikshitnarang/Pinholeproject"
SRC_DIR = os.path.join(ROOT, "ExP1")
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "brisque_model", "brisque_model_live.yml")
RANGE = os.path.join(HERE, "brisque_model", "brisque_range_live.yml")
SCRATCH = "/tmp/exp1_brisque_scratch"
os.makedirs(SCRATCH, exist_ok=True)

OUT_DIRS = [SRC_DIR, os.path.join(HERE, "measurements")]
for d in OUT_DIRS:
    os.makedirs(d, exist_ok=True)

FOLDERS = ["400", "500", "700", "1000", "1200", "1400", "M1-8 no pinhole"]


def dng_to_u8(dng_path):
    tiff_path = os.path.join(SCRATCH, os.path.basename(dng_path) + ".tiff")
    try:
        subprocess.run(["sips", "-s", "format", "tiff", dng_path, "--out", tiff_path],
                        capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return None
    if not os.path.exists(tiff_path):
        return None
    bgr = cv2.imread(tiff_path, cv2.IMREAD_UNCHANGED)
    os.remove(tiff_path)
    if bgr is None:
        return None
    if bgr.ndim == 2:
        bgr = np.stack([bgr] * 3, axis=-1)
    f = bgr.astype(np.float64)
    lo, hi = np.percentile(f, [1.0, 99.5])
    if hi <= lo:
        hi = lo + 1.0
    stretched = np.clip((f - lo) / (hi - lo), 0, 1) * 255.0
    return stretched.astype(np.uint8)


def main():
    rows = []
    for folder in FOLDERS:
        d = os.path.join(SRC_DIR, folder)
        if not os.path.isdir(d):
            print(f"[skip] {folder}: not found")
            continue
        for fname in sorted(os.listdir(d)):
            if not fname.lower().endswith(".dng"):
                continue
            path = os.path.join(d, fname)
            img_u8 = dng_to_u8(path)
            if img_u8 is None:
                rows.append({"folder": folder, "filename": fname, "brisque_score": None,
                             "note": "conversion/read failed or timed out"})
                print(f"[FAIL] {folder}/{fname}", flush=True)
                continue
            score = cv2.quality.QualityBRISQUE_compute(img_u8, MODEL, RANGE)[0]
            rows.append({"folder": folder, "filename": fname, "brisque_score": round(score, 4),
                         "note": ""})
            print(f"[ok] {folder}/{fname}: BRISQUE={score:.4f}", flush=True)

        # checkpoint after every folder -- so a later hang doesn't lose completed work
        pd.DataFrame(rows).to_csv(os.path.join(HERE, "measurements", "_checkpoint.csv"), index=False)

    df = pd.DataFrame(rows)
    df["rank_within_folder"] = df.groupby("folder")["brisque_score"].rank(method="min")

    for d in OUT_DIRS:
        csv_path = os.path.join(d, "brisque_scores.csv")
        xlsx_path = os.path.join(d, "brisque_scores.xlsx")
        df.to_csv(csv_path, index=False)
        df.to_excel(xlsx_path, index=False, sheet_name="brisque_scores")
        print(f"wrote {csv_path}")
        print(f"wrote {xlsx_path}")

    summary = df.groupby("folder")["brisque_score"].agg(["count", "mean", "median", "std"]).reset_index()
    summary = summary.sort_values("mean")
    print("\n--- per-aperture BRISQUE summary (lower mean = better quality) ---")
    print(summary.to_string(index=False))
    for d in OUT_DIRS:
        summary.to_csv(os.path.join(d, "brisque_summary_per_aperture.csv"), index=False)


if __name__ == "__main__":
    main()
