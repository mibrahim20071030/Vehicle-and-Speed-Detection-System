from counting import crossed, iou, make_counter_state, update_counts

A, B = (100, 300), (800, 300)


def make_track(track_id, cx, bottom_y):
    return {"track_id": track_id, "box": (cx - 20, bottom_y - 40, cx + 20, bottom_y), "class_id": 2, "confidence": 0.9}


def run_sequence(bottom_ys):
    state = make_counter_state()
    for y in bottom_ys:
        update_counts(state, [make_track(1, 400, y)], A, B)
    return state["counts"]


def test_iou():
    assert abs(iou((0, 0, 10, 10), (5, 0, 15, 10)) - 1 / 3) < 1e-9
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (20, 0, 30, 10)) == 0


def test_crossing_detected():
    assert crossed(A, B, (400, 297), (400, 305))


def test_no_crossing_same_side():
    assert not crossed(A, B, (400, 290), (400, 297))


def test_path_beyond_line_end_not_counted():
    assert not crossed(A, B, (900, 297), (900, 305))


def test_vehicle_counted_once_going_down():
    assert run_sequence([280, 290, 297, 305, 315, 295, 310]) == {"positive": 1, "negative": 0}


def test_vehicle_going_up_counts_negative():
    assert run_sequence([320, 310, 303, 295, 285]) == {"positive": 0, "negative": 1}


def test_first_frame_never_counts():
    assert run_sequence([305]) == {"positive": 0, "negative": 0}
