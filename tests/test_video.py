import numpy as np
import pytest

from helpers import make_video
from video import draw_overlay, open_video


def test_read_video(tmp_path):
    path = tmp_path / "gray.mp4"
    make_video(path)

    cap, fps = open_video(path)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()

    assert len(frames) == 10
    for frame in frames:
        assert frame.shape == (48, 64, 3)


def test_open_video_bad_path():
    with pytest.raises(ValueError):
        open_video("missing.mp4")


def test_draw_overlay_draws_line_on_copy():
    frame = np.zeros((100, 200, 3), np.uint8)
    out = draw_overlay(frame, (10, 50), (190, 50))

    assert list(out[50, 100]) == [0, 255, 0]
    assert not frame.any()
