import math

import cv2
import numpy as np


def build_homography(src, dst):
    """Fit the pixel-to-meter homography H from N >= 4 matching points (src in pixels, dst in meters).

    The fit runs meters-to-pixels so the least-squares error is measured in pixels, then H is inverted.
    """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    if src.ndim != 2 or src.shape[1] != 2 or src.shape != dst.shape:
        raise ValueError("src and dst must both have shape (N, 2)")
    if len(src) < 4:
        raise ValueError("Need at least 4 points")

    H_m2p, _ = cv2.findHomography(dst, src, 0)
    if H_m2p is None:
        raise ValueError("findHomography failed")
    H = np.linalg.inv(H_m2p)
    return H / H[2, 2]


def to_meters(H, x, y):
    """Convert pixel (x, y) to road position (X, Y) in meters."""
    a, b, w = H @ np.array([x, y, 1.0])
    return (a / w, b / w)


def check_calibration(H, pixel_a, pixel_b, known_m):
    """Measure the distance between two road pixels with H and compare it with a known distance in meters.

    Returns (measured_m, percent_error). Use two points that were NOT used to build H.
    """
    pa = to_meters(H, *pixel_a)
    pb = to_meters(H, *pixel_b)
    measured_m = float(math.dist(pa, pb))
    percent_error = abs(measured_m - known_m) / known_m * 100
    return measured_m, percent_error
