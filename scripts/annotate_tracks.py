"""Layer 3 visual check: write a copy of the first frames of a clip with tracked boxes and their IDs drawn.

Usage (from the repo root):
    python scripts/annotate_tracks.py "footage/Untitled design.mp4" footage/annotated_tracks.mp4 [max_frames]

max_frames defaults to 300 (10 s at 30 fps).
"""
import sys
from collections import Counter
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LINE_A, LINE_B  # noqa: E402
from tracker import make_tracker, track_frame  # noqa: E402
from video import draw_overlay, open_video  # noqa: E402


def main(in_path, out_path, max_frames=300):
    cap, fps = open_video(in_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    tracker = make_tracker()

    frames = 0
    frames_with_tracks = 0
    id_counts = Counter()
    while frames < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        tracks = track_frame(tracker, frame)
        frames += 1
        if tracks:
            frames_with_tracks += 1
        for t in tracks:
            id_counts[t["track_id"]] += 1
        writer.write(draw_overlay(frame, LINE_A, LINE_B, tracks=tracks))

    cap.release()
    writer.release()
    print(f"Wrote {frames} frames ({width}x{height} @ {fps:.2f} fps) to {out_path}")
    print(f"Frames with tracks: {frames_with_tracks}, unique track IDs: {len(id_counts)}")
    if id_counts:
        lengths = sorted(id_counts.values())
        print(f"Frames per ID: min {lengths[0]}, median {lengths[len(lengths) // 2]}, max {lengths[-1]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 300)
