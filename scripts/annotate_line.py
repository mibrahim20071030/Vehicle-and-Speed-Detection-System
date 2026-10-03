"""Layer 1 manual check: write a copy of a clip with the counting line drawn on every frame.

Usage (from the repo root):
    python scripts/annotate_line.py footage/traffic.mp4 annotated_line.mp4
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LINE_A, LINE_B  # noqa: E402
from video import draw_overlay, open_video  # noqa: E402


def main(in_path, out_path):
    cap, fps = open_video(in_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(draw_overlay(frame, LINE_A, LINE_B))
        n += 1

    cap.release()
    writer.release()
    print(f"Wrote {n} frames ({width}x{height} @ {fps:.2f} fps) to {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
