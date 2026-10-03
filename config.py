"""Camera setup, loaded from calibration_points.json so the numbers are never copied by hand.

The pixel positions are measurements. The meter values are an assumed NYSDOT lane-marking
standard (not independently verified); see "assumptions" in calibration_points.json.
"""
import json
from pathlib import Path

import numpy as np

_DATA = json.loads((Path(__file__).parent / "calibration_points.json").read_text())

SRC = np.array([p["pixel"] for p in _DATA["points"]], dtype=np.float32)    # pixels, shape (21, 2)
DST = np.array([p["meters"] for p in _DATA["points"]], dtype=np.float32)   # meters, shape (21, 2)  # ASSUMED
LINE_A = tuple(_DATA["line_a"])
LINE_B = tuple(_DATA["line_b"])
ZONE = tuple(_DATA["zone_m"])  # ASSUMED (meters, same assumed scale as DST)
FRAME_SIZE = tuple(_DATA["frame_size"])
