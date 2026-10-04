import math

from calibration import to_meters
from counting import reference_point


def speed_kmh(p0, p1, frame0, frame1, fps):
    """Speed in km/h between road positions p0 and p1 (meters), seen at frame0 and frame1 of a video at fps."""
    return math.dist(p0, p1) / ((frame1 - frame0) / fps) * 3.6


def make_speed_state():
    """Empty speed state for one video."""
    return {"positions": {}}


def update_speeds(state, tracks, H, frame_idx, fps, window=10, zone=None):
    """Store each track's road position this frame and return {track_id: km/h} for tracks with enough history.

    zone = (x_min, x_max, y_min, y_max) in meters. Tracks outside it are skipped this frame.
    Speed compares the newest entry with the one `window` entries earlier, using their stored frame numbers.
    """
    speeds = {}
    for t in tracks:
        X, Y = to_meters(H, *reference_point(t["box"]))
        X, Y = float(X), float(Y)
        if zone is not None and not (zone[0] <= X <= zone[1] and zone[2] <= Y <= zone[3]):
            continue
        history = state["positions"].setdefault(t["track_id"], [])
        history.append((frame_idx, X, Y))
        if len(history) > window:
            f0, X0, Y0 = history[-1 - window]
            f1, X1, Y1 = history[-1]
            speeds[t["track_id"]] = speed_kmh((X0, Y0), (X1, Y1), f0, f1, fps)
    return speeds
