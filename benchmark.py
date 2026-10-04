"""Layer 7: run the pipeline with yolo26 n / s / m on the same clip and print a results table.

Usage (from the repo root):
    python benchmark.py
"""
import platform
import sys

import cv2

from config import DST, LINE_A, LINE_B, SRC, ZONE
from metrics import percent_error, speed_errors
from pipeline import process_video

MODELS = ["yolo26n.pt", "yolo26s.pt", "yolo26m.pt"]


def run_benchmark(count_clip, hand_counts, speed_clips, start_frame=0, end_frame=None):
    """Run every model in MODELS on the count clip (frames start_frame to end_frame - 1) and on each speed clip.

    hand_counts: {"positive": n, "negative": m}, counted by hand with the program's definition.
    speed_clips: list of (clip_path, true_kmh). A speed clip is used only if exactly 1 vehicle gets a speed.
    Returns one dict per model. A count error is None where the hand count for that direction is 0.
    """
    results = []
    for model_name in MODELS:
        # no output_path: writing a video slows the program down and would distort processing_fps
        r = process_video(count_clip, SRC, DST, LINE_A, LINE_B, model_name=model_name, zone=ZONE,
                          start_frame=start_frame, end_frame=end_frame)
        err_pos = percent_error(r["counts"]["positive"], hand_counts["positive"])
        err_neg = percent_error(r["counts"]["negative"], hand_counts["negative"])
        known = [e for e in (err_pos, err_neg) if e is not None]

        predicted, truth, used = [], [], []
        for clip_path, true_kmh in speed_clips:
            with_speed = [v for v in process_video(clip_path, SRC, DST, LINE_A, LINE_B, model_name=model_name,
                                                   zone=ZONE)["vehicles"] if v["speed_kmh"] is not None]
            if len(with_speed) == 1:
                predicted.append(with_speed[0]["speed_kmh"])
                truth.append(true_kmh)
                used.append(str(clip_path))

        results.append({
            "model": model_name,
            "frames_processed": r["frames_processed"],
            "start_frame": r["start_frame"],
            "end_frame": r["end_frame"],
            "counts": r["counts"],
            "count_error_pct": {
                "positive": err_pos,
                "negative": err_neg,
                "total": sum(known) if known else None,
            },
            "processing_fps": r["processing_fps"],
            "speed_errors": speed_errors(predicted, truth) if used else None,
            "speed_clips_used": used,
        })
    return results


def _pct(value):
    return "n/a" if value is None else f"{value:.1f}%"


def print_environment():
    import torch
    import ultralytics

    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none (CPU only)"
    cpu = platform.processor()
    if sys.platform == "win32":  # platform.processor() gives only the family code on Windows
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    print(f"- GPU: {gpu}")
    print(f"- CPU: {cpu}")
    print(f"- OS: {platform.platform()}")
    print(f"- Python {platform.python_version()}, torch {torch.__version__}, "
          f"ultralytics {ultralytics.__version__}, opencv {cv2.__version__}")


if __name__ == "__main__":
    COUNT_CLIP = "footage/Untitled design.mp4"
    START_FRAME, END_FRAME = 1800, 3600  # 60.0 to 120.0 s, the reported minute
    HAND_COUNTS = {"positive": 83, "negative": 0}  # user's hand count of 60 to 120 s from footage/count_60_120.mp4 (2026-10-04)
    SPEED_CLIPS = []  # (clip_path, true_kmh); none for this footage

    if sys.argv[1:2] == ["--short"]:  # quick check of the code path on 1 s, not a result
        END_FRAME = START_FRAME + 30

    print_environment()
    print()
    rows = run_benchmark(COUNT_CLIP, HAND_COUNTS, SPEED_CLIPS, START_FRAME, END_FRAME)

    print(f"Frames {START_FRAME} to {END_FRAME - 1} of {COUNT_CLIP}. "
          f"Hand count: +{HAND_COUNTS['positive']} / -{HAND_COUNTS['negative']}.")
    print()
    print("| Model | Counts (+/-), program vs hand | + error | - error | Count error "
          "| Speed MAE | Speed bias | Speed MAPE | FPS |")
    print("|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        c, e, s = row["counts"], row["count_error_pct"], row["speed_errors"]
        speed_cells = ("n/a", "n/a", "n/a") if s is None else (
            f"{s['mae_kmh']:.1f} km/h", f"{s['bias_kmh']:+.1f} km/h", f"{s['mape_pct']:.1f}%")
        print(f"| {row['model']} "
              f"| +{c['positive']}/{HAND_COUNTS['positive']}, -{c['negative']}/{HAND_COUNTS['negative']} "
              f"| {_pct(e['positive'])} | {_pct(e['negative'])} | {_pct(e['total'])} "
              f"| {' | '.join(speed_cells)} | {row['processing_fps']:.1f} |")
    for direction, sign in (("negative", "-"), ("positive", "+")):
        other = "+" if sign == "-" else "-"
        if HAND_COUNTS[direction] == 0:
            print(f"\nHand count for {sign} is 0, so the count error comes from the {other} direction only.")
    print(f"\nSpeed clips used: {rows[0]['speed_clips_used'] or 'none'}")
