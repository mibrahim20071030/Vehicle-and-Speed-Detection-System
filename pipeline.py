import time

import cv2

from calibration import build_homography
from counting import make_counter_state, update_counts
from speed import make_speed_state, update_speeds
from tracker import make_tracker, track_frame
from video import draw_overlay, open_video

CLASS_NAMES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
WARMUP_FRAMES = 5  # frames run before the processing-speed timer starts (model warm-up)


def process_video(path, src, dst, line_a, line_b, window=10, model_name="yolo26n.pt",
                  zone=None, output_path=None, start_frame=0, end_frame=None):
    """Track, count and measure the speed of vehicles in a video. Returns a summary dict.

    Only frames start_frame to end_frame - 1 are processed (end_frame=None means to the end).
    Frame numbers stay those of the full video. If output_path is given, an annotated copy is written there.
    """
    cap, fps = open_video(path)
    H = build_homography(src, dst)
    tracker = make_tracker(model_name)
    counter_state = make_counter_state()
    speed_state = make_speed_state()
    class_of = {}      # {track_id: class_id}, class seen in the track's latest frame
    speed_lists = {}   # {track_id: [every speed measured, km/h]}

    writer = None
    if output_path is not None:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    frame_idx = 0
    frames_processed = 0
    start_time = None
    try:
        # skip to start_frame by grabbing (no decoding); exact, unlike seeking in an mp4
        while frame_idx < start_frame and cap.grab():
            frame_idx += 1

        while end_frame is None or frame_idx < end_frame:
            if frames_processed == WARMUP_FRAMES:
                start_time = time.perf_counter()
            ok, frame = cap.read()
            if not ok:
                break

            tracks = track_frame(tracker, frame)
            update_counts(counter_state, tracks, line_a, line_b)
            speeds = update_speeds(speed_state, tracks, H, frame_idx, fps, window=window, zone=zone)
            for t in tracks:
                class_of[t["track_id"]] = t["class_id"]
            for track_id, kmh in speeds.items():
                speed_lists.setdefault(track_id, []).append(kmh)

            if writer is not None:
                writer.write(draw_overlay(frame, line_a, line_b, tracks, counter_state["counts"], speeds))

            frame_idx += 1
            frames_processed += 1
    finally:
        cap.release()
        if writer is not None:
            writer.release()

    processing_fps = None
    if frames_processed > WARMUP_FRAMES:
        processing_fps = (frames_processed - WARMUP_FRAMES) / (time.perf_counter() - start_time)

    # a vehicle is listed if it crossed the line, got a speed, or both
    counted_ids = counter_state["counted_ids"]
    vehicles = []
    for track_id in sorted(counted_ids | speed_lists.keys()):
        speed_list = speed_lists.get(track_id)
        vehicles.append({
            "track_id": track_id,
            "class": CLASS_NAMES.get(class_of.get(track_id), "unknown"),
            "speed_kmh": round(sum(speed_list) / len(speed_list), 1) if speed_list else None,
            "counted": track_id in counted_ids,
        })

    return {
        "model": model_name,
        "frames_processed": frames_processed,
        "fps": fps,
        "processing_fps": processing_fps,
        "start_frame": start_frame,
        "end_frame": frame_idx,
        "counts": dict(counter_state["counts"]),
        "vehicles": vehicles,
    }
