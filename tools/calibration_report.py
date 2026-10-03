"""Print the calibration fit quality, the held-out row 3 test, and the edge line check.

Usage (from the repo root):
    python tools/calibration_report.py
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from calibration import build_homography, to_meters  # noqa: E402
from config import DST, SRC  # noqa: E402

NAMES = [p["name"] for p in json.loads((ROOT / "calibration_points.json").read_text())["points"]]

# Baseline from the rounded JSON values (see CLAUDE.md, "Calibration decisions").
BASELINE = {"pixel_rms": 2.78, "pixel_max": 4.98, "meter_rms": 0.164, "meter_max": 0.370}

EDGE_LINE_PIXELS = [(1503, 1080), (1657, 1004), (1825, 920)]


def fit_errors(H, src, dst):
    """Return (pixel errors, meter errors) for each point under H (pixel to meter)."""
    proj = cv2.perspectiveTransform(dst.reshape(-1, 1, 2).astype(np.float64), np.linalg.inv(H)).reshape(-1, 2)
    pixel_err = np.linalg.norm(proj - src, axis=1)
    meter_err = np.array([np.linalg.norm(np.array(to_meters(H, *p)) - w) for p, w in zip(src, dst)])
    return pixel_err, meter_err


def rms(v):
    return float(np.sqrt(np.mean(np.square(v))))


def main():
    src = SRC.astype(np.float64)
    dst = DST.astype(np.float64)

    print("=== Fit with all 21 points ===")
    H = build_homography(src, dst)
    pe, me = fit_errors(H, src, dst)
    print(f"Pixel reprojection error RMS / max: {rms(pe):.2f} / {pe.max():.2f} px"
          f"   (baseline {BASELINE['pixel_rms']} / {BASELINE['pixel_max']})")
    print(f"Meter position error     RMS / max: {rms(me):.3f} / {me.max():.3f} m"
          f"   (baseline {BASELINE['meter_rms']} / {BASELINE['meter_max']})")
    worst = int(np.argmax(pe))
    print(f"Worst point: {NAMES[worst]} ({pe[worst]:.2f} px, {me[worst]:.3f} m)")

    print("\n=== Held-out test: fit rows 1 and 2, predict row 3 ===")
    fit = np.array(["row3" not in n for n in NAMES])
    H12 = build_homography(src[fit], dst[fit])
    held_err = []
    for i in np.where(~fit)[0]:
        X, Y = to_meters(H12, *src[i])
        err = float(np.hypot(X - dst[i][0], Y - dst[i][1]))
        held_err.append(err)
        print(f"  {NAMES[i]:<18} predicted ({X:6.2f}, {Y:6.2f})  true ({dst[i][0]:6.2f}, {dst[i][1]:6.2f})  error {err:.2f} m")
    print(f"Mean error {np.mean(held_err):.2f} m (range {min(held_err):.2f} to {max(held_err):.2f})"
          "   (baseline about 0.35, range 0.17 to 0.67)")

    print("\nRow 2 to row 3 spacing from the held-out fit (true 12.19 m; baseline about 12.16, 12.50, 12.78):")
    idx = {n: i for i, n in enumerate(NAMES)}
    for line in "abc":
        p2 = to_meters(H12, *src[idx[f"line{line}_row2_start"]])
        p3 = to_meters(H12, *src[idx[f"line{line}_row3_start"]])
        print(f"  line {line}: {np.hypot(p3[0] - p2[0], p3[1] - p2[1]):.2f} m")

    print("\n=== Edge line check (solid right edge line, X should be constant) ===")
    for p in EDGE_LINE_PIXELS:
        X, Y = to_meters(H, *p)
        print(f"  pixel {p} -> X = {X:.2f} m, Y = {Y:.2f} m")
    print("  (baseline X about -4.40, -4.39, -4.33)")

    print("\nThese are consistency checks. They use the same lane-marking assumption,"
          " so they do NOT verify the absolute scale.")


if __name__ == "__main__":
    main()
