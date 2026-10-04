"""Layer 6 demo: run the full pipeline on part of the calibration clip, write an annotated video and demo.gif.

Usage (from the repo root):
    python scripts/make_demo.py [start_s] [seconds]

start_s defaults to 0 and seconds to 10. Writes footage/annotated_demo.mp4 (git-ignored) and demo.gif
(10 fps, 640 px wide, made with Pillow because ffmpeg is not installed here).
"""
import json
import sys
from pathlib import Path

import cv2
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DST, LINE_A, LINE_B, SRC, ZONE  # noqa: E402
from pipeline import process_video  # noqa: E402
from video import open_video  # noqa: E402

CLIP = ROOT / "footage" / "Untitled design.mp4"
OUT_VIDEO = ROOT / "footage" / "annotated_demo.mp4"
OUT_GIF = ROOT / "demo.gif"
GIF_FPS = 10
GIF_WIDTH = 640


def write_gif(video_path, gif_path):
    """Turn the annotated video into a GIF at GIF_FPS frames per second, GIF_WIDTH pixels wide."""
    cap, fps = open_video(video_path)
    step = max(round(fps / GIF_FPS), 1)  # keep every step-th frame
    images = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            h, w = frame.shape[:2]
            small = cv2.resize(frame, (GIF_WIDTH, round(h * GIF_WIDTH / w)), interpolation=cv2.INTER_AREA)
            images.append(Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)))
        i += 1
    cap.release()
    images[0].save(gif_path, save_all=True, append_images=images[1:], duration=1000 // GIF_FPS, loop=0)
    return len(images)


def main(start_s=0.0, seconds=10.0):
    _, fps = open_video(CLIP)
    start_frame = round(start_s * fps)
    end_frame = start_frame + round(seconds * fps)
    result = process_video(CLIP, SRC, DST, LINE_A, LINE_B, zone=ZONE, output_path=OUT_VIDEO,
                           start_frame=start_frame, end_frame=end_frame)
    print(json.dumps(result, indent=2))
    n = write_gif(OUT_VIDEO, OUT_GIF)
    print(f"Wrote {OUT_VIDEO} and {OUT_GIF} ({n} GIF frames)")


if __name__ == "__main__":
    main(*(float(a) for a in sys.argv[1:3]))
