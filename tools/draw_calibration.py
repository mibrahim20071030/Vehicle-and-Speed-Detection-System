"""Draw the calibration on frame 0 of a video: metric grid, the 21 points, the counting line, and ZONE.

Usage (from the repo root):
    python tools/draw_calibration.py "footage/Untitled design.mp4" overlay.png
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calibration import build_homography  # noqa: E402
from config import DST, FRAME_SIZE, LINE_A, LINE_B, SRC, ZONE  # noqa: E402
from video import draw_overlay, open_video  # noqa: E402

LANE_M = 3.6576   # ASSUMED, same as calibration_points.json
CYCLE_M = 12.192  # ASSUMED, same as calibration_points.json

GRID_COLOR = (0, 255, 255)    # yellow
POINT_COLOR = (0, 0, 255)     # red
ZONE_COLOR = (255, 255, 0)    # cyan


def to_pixels(H, points_m):
    """Map an (N, 2) array of meter positions to pixels with the inverse of H."""
    pts = np.asarray(points_m, dtype=np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, np.linalg.inv(H)).reshape(-1, 2)


def draw_segment(img, H, p0_m, p1_m, color, thickness):
    # A homography maps straight lines to straight lines, so the two ends are enough.
    (x0, y0), (x1, y1) = to_pixels(H, [p0_m, p1_m])
    cv2.line(img, (int(round(x0)), int(round(y0))), (int(round(x1)), int(round(y1))),
             color, thickness, cv2.LINE_AA)


def main(video_path, out_path):
    cap, _ = open_video(video_path)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("Could not read frame 0")

    h, w = frame.shape[:2]
    if (w, h) != tuple(FRAME_SIZE):
        print(f"WARNING: frame is {w}x{h}, calibration is for {FRAME_SIZE[0]}x{FRAME_SIZE[1]}. "
              "Drawing in calibration pixels anyway.")

    H = build_homography(SRC, DST)
    img = draw_overlay(frame, LINE_A, LINE_B)  # (ours) counting line, green

    y_min, y_max = ZONE[2], ZONE[3]
    x_lo, x_hi = -1 * LANE_M, 4 * LANE_M
    for k in range(-1, 5):                   # lane lines, constant X
        draw_segment(img, H, (k * LANE_M, y_min), (k * LANE_M, y_max), GRID_COLOR, 1)
    for r in range(3):                       # dash rows, constant Y
        draw_segment(img, H, (x_lo, r * CYCLE_M), (x_hi, r * CYCLE_M), GRID_COLOR, 1)

    corners_m = [(ZONE[0], ZONE[2]), (ZONE[1], ZONE[2]), (ZONE[1], ZONE[3]), (ZONE[0], ZONE[3])]
    zone_px = np.round(to_pixels(H, corners_m)).astype(np.int32)
    cv2.polylines(img, [zone_px], True, ZONE_COLOR, 2, cv2.LINE_AA)

    for x, y in SRC:
        cv2.circle(img, (int(round(x)), int(round(y))), 5, POINT_COLOR, 2, cv2.LINE_AA)

    cv2.putText(img, f"{Path(video_path).name}  frame 0  {w}x{h}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, "yellow: grid  red: 21 points  green: counting line  cyan: ZONE", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.imwrite(str(out_path), img)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
