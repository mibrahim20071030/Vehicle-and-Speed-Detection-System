"""Layer 1 manual check: write a copy of a clip with the counting line drawn on every frame.

Also used for the Layer 7 hand count: give a time range, and every frame gets its time (s) and its
frame number in the full video, so crossings can be written down.

Usage (from the repo root):
    python scripts/annotate_line.py footage/traffic.mp4 annotated_line.mp4 [start_s] [end_s]

start_s defaults to 0, end_s to the end of the clip.
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LINE_A, LINE_B  # noqa: E402
from video import draw_overlay, open_video  # noqa: E402

STAMP_COLOR = (0, 255, 255)  # yellow (BGR)
STAMP_BG_COLOR = (0, 0, 0)
STAMP_SCALE = 1.2


def draw_stamp(frame, frame_idx, fps):
    """Draw 't = 60.00 s  frame 1800' in the top-left corner on a black box. Changes frame in place."""
    text = f"t = {frame_idx / fps:.2f} s  frame {frame_idx}"
    (w, h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, STAMP_SCALE, 2)
    cv2.rectangle(frame, (10, 10), (30 + w, 30 + h + baseline), STAMP_BG_COLOR, -1)
    cv2.putText(frame, text, (20, 20 + h), cv2.FONT_HERSHEY_SIMPLEX, STAMP_SCALE, STAMP_COLOR, 2)


def main(in_path, out_path, start_s=0.0, end_s=None):
    cap, fps = open_video(in_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_frame = round(start_s * fps)
    end_frame = None if end_s is None else round(end_s * fps)

    # skip to start_frame by grabbing (no decoding); exact, unlike seeking in an mp4
    frame_idx = 0
    while frame_idx < start_frame and cap.grab():
        frame_idx += 1

    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    n = 0
    while end_frame is None or frame_idx < end_frame:
        ok, frame = cap.read()
        if not ok:
            break
        out = draw_overlay(frame, LINE_A, LINE_B)
        draw_stamp(out, frame_idx, fps)
        writer.write(out)
        frame_idx += 1
        n += 1

    cap.release()
    writer.release()
    print(f"Wrote {n} frames (frames {start_frame} to {frame_idx - 1}, {width}x{height} @ {fps:.2f} fps) to {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *(float(a) for a in sys.argv[3:5]))
