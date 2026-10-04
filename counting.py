def side_of_line(a, b, p):
    """Which side of the line from a to b point p is on. Only the sign matters."""
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def iou(a, b):
    """Intersection over union of two boxes (x1, y1, x2, y2). 0 = no overlap, 1 = identical."""
    ox1, oy1 = max(a[0], b[0]), max(a[1], b[1])
    ox2, oy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ox2 - ox1) * max(0, oy2 - oy1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def crossed(a, b, prev, curr):
    """True if the path from prev to curr crosses the line segment from a to b."""
    s1, s2 = side_of_line(a, b, prev), side_of_line(a, b, curr)
    t1, t2 = side_of_line(prev, curr, a), side_of_line(prev, curr, b)
    return (s1 * s2 < 0) and (t1 * t2 < 0)


def reference_point(box):
    """Bottom-center of a box (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, y2)


def make_counter_state():
    """Empty counter state for one video."""
    return {"last_point": {}, "counted_ids": set(), "counts": {"positive": 0, "negative": 0}}


def update_counts(state, tracks, a, b):
    """Count tracks whose reference point crossed the line a-b since the last frame. Changes state in place."""
    for t in tracks:
        track_id = t["track_id"]
        curr = reference_point(t["box"])
        prev = state["last_point"].get(track_id)
        if prev is not None and track_id not in state["counted_ids"] and crossed(a, b, prev, curr):
            state["counted_ids"].add(track_id)
            if side_of_line(a, b, curr) > 0:
                state["counts"]["positive"] += 1
            else:
                state["counts"]["negative"] += 1
        state["last_point"][track_id] = curr
