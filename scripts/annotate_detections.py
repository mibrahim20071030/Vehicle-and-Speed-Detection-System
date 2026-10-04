"""Layer 2 visual check: write a copy of the first frames of a clip with detection boxes drawn.

Usage (from the repo root):
    python scripts/annotate_detections.py "footage/Untitled design.mp4" footage/annotated_detections.mp4 [max_frames]

max_frames defaults to 300 (10 s at 30 fps).
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LINE_A, LINE_B  # noqa: E402
from detector import detect  # noqa: E402
from video import draw_overlay, open_video  # noqa: E402


def main(in_path, out_path, max_frames=300):
    cap, fps = open_video(in_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    per_frame = []
    while len(per_frame) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        detections = detect(frame)
        per_frame.append(len(detections))
        writer.write(draw_overlay(frame, LINE_A, LINE_B, tracks=detections))

    cap.release()
    writer.release()
    print(f"Wrote {len(per_frame)} frames ({width}x{height} @ {fps:.2f} fps) to {out_path}")
    if per_frame:
        print(f"Detections per frame: average {sum(per_frame) / len(per_frame):.1f}, "
              f"min {min(per_frame)}, max {max(per_frame)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 300)
