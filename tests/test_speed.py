import numpy as np
import pytest

from calibration import build_homography, check_calibration, to_meters
from speed import make_speed_state, speed_kmh, update_speeds

SQUARE_SRC = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)  # pixels
SQUARE_DST = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)  # meters (100 px = 1 m)


def test_calibration_points_map_to_destination():
    # Rewritten: a 4-point case fits exactly. The 21-point config check is test_fit_quality.
    H = build_homography(SQUARE_SRC, SQUARE_DST)
    for p, w in zip(SQUARE_SRC, SQUARE_DST):
        X, Y = to_meters(H, *p)
        assert abs(X - w[0]) < 1e-3 and abs(Y - w[1]) < 1e-3


def test_check_calibration_known_scale():
    H = build_homography(SQUARE_SRC, SQUARE_DST)
    measured_m, percent_error = check_calibration(H, (0, 0), (300, 400), 5.0)
    assert measured_m == pytest.approx(5.0, abs=1e-3)
    assert percent_error < 0.01


def test_speed_kmh_345():
    assert speed_kmh((0, 0), (3, 4), 0, 30, 30) == pytest.approx(18)


def test_speed_kmh_36():
    assert speed_kmh((0, 0), (0, 5), 0, 15, 30) == pytest.approx(36)


def _track_at(frame_idx):
    # ID 1, reference point (100, 100 + frame_idx): moves 1 unit per frame
    return [{"track_id": 1, "box": (90, 60 + frame_idx, 110, 100 + frame_idx)}]


def test_update_speeds_constant_motion():
    H = np.eye(3)  # pixels act as meters
    state = make_speed_state()
    for frame_idx in range(13):
        speeds = update_speeds(state, _track_at(frame_idx), H, frame_idx, fps=10, window=10)
        if frame_idx <= 9:
            assert speeds == {}
    # 10 m in 10 frames at 10 fps = 10 m/s = 36 km/h
    assert speeds == {1: pytest.approx(36)}


def test_update_speeds_outside_zone():
    H = np.eye(3)
    state = make_speed_state()
    for frame_idx in range(13):
        speeds = update_speeds(state, _track_at(frame_idx), H, frame_idx, fps=10, window=10,
                               zone=(0, 1000, 0, 50))
        assert speeds == {}
