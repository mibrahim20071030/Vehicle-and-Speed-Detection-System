import numpy as np
from calibration import build_homography, to_meters
from counting import side_of_line
from config import SRC, DST, LINE_A, LINE_B, ZONE


def _in_zone(x, y):
    return ZONE[0] <= x <= ZONE[1] and ZONE[2] <= y <= ZONE[3]


def test_config_shapes():
    assert SRC.shape == DST.shape and SRC.shape[1] == 2 and len(SRC) == 21


def test_fit_quality():
    H = build_homography(SRC, DST)
    errs = [np.linalg.norm(np.array(to_meters(H, *p)) - w) for p, w in zip(SRC, DST)]
    assert np.sqrt(np.mean(np.square(errs))) < 0.25
    assert max(errs) < 0.5


def test_near_lane_pixels_inside_zone():
    H = build_homography(SRC, DST)
    assert _in_zone(*to_meters(H, 900, 960))      # near lane
    assert _in_zone(*to_meters(H, 1500, 930))     # near lane


def test_far_lane_and_edge_pixels_outside_zone():
    H = build_homography(SRC, DST)
    for p in [(1000, 800), (600, 790), (100, 850), (1400, 790)]:
        assert not _in_zone(*to_meters(H, *p))


def test_line_inside_frame():
    for p in (LINE_A, LINE_B):
        assert 0 <= p[0] < 1920 and 0 <= p[1] < 1080


def test_positive_direction_is_left_to_right():
    # a point after the line (larger Y) must be on the positive side
    after = (1518.0, 853.5)      # line b, row 3 start (Y = 24.38)
    before = (763.8, 1031.4)     # line b, row 1 start (Y = 0)
    assert side_of_line(LINE_A, LINE_B, after) > 0
    assert side_of_line(LINE_A, LINE_B, before) < 0
