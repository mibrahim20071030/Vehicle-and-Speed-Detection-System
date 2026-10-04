import cv2
import numpy as np

from detector import detect


def test_detect_returns_vehicles():
    frame = cv2.imread("tests/data/car.jpg")
    assert frame is not None

    detections = detect(frame)

    assert len(detections) >= 1
    for d in detections:
        x1, y1, x2, y2 = d["box"]
        assert d["class_id"] in (2, 3, 5, 7)
        assert 0 <= d["confidence"] <= 1
        assert x1 < x2
        assert y1 < y2


def test_detect_blank_frame():
    assert detect(np.zeros((480, 640, 3), np.uint8)) == []
