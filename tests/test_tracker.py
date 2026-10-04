from collections import Counter

import numpy as np

from tracker import make_tracker, track_frame
from video import open_video


def test_one_vehicle_keeps_one_id():
    cap, _ = open_video("tests/data/one_car.mp4")
    tracker = make_tracker()
    id_counts = Counter()
    frames_with_tracks = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        tracks = track_frame(tracker, frame)
        if tracks:
            frames_with_tracks += 1
        for t in tracks:
            id_counts[t["track_id"]] += 1
    cap.release()

    assert frames_with_tracks > 0
    _, most_common_count = id_counts.most_common(1)[0]
    assert most_common_count >= 0.8 * frames_with_tracks


def test_blank_frames_have_no_tracks():
    tracker = make_tracker()
    for _ in range(3):
        assert track_frame(tracker, np.zeros((480, 640, 3), np.uint8)) == []
