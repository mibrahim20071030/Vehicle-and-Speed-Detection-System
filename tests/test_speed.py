import numpy as np

from calibration import build_homography, to_meters


def test_calibration_points_map_to_destination():
    # Rewritten: a 4-point case fits exactly. The 21-point config check is test_fit_quality.
    src = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
    dst = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)
    H = build_homography(src, dst)
    for p, w in zip(src, dst):
        X, Y = to_meters(H, *p)
        assert abs(X - w[0]) < 1e-3 and abs(Y - w[1]) < 1e-3
