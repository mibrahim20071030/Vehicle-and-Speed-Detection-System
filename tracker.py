from ultralytics import YOLO


def make_tracker(model_name="yolo26n.pt"):
    """Return a NEW YOLO model to track with. Make one per video: it remembers tracks between calls."""
    return YOLO(model_name)


def track_frame(tracker_model, frame):
    """Track vehicles in one frame. Returns a list of {"track_id", "box", "class_id", "confidence"} dicts."""
    # agnostic_nms: merge overlapping boxes even if their classes differ, so a van seen as both
    # car and truck gets one box (and one count), not two
    r = tracker_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.1, iou=0.5,
                            classes=[2, 3, 5, 7], agnostic_nms=True, verbose=False)[0]
    if r.boxes.id is None:
        return []
    ids = r.boxes.id.tolist()
    boxes = r.boxes.xyxy.tolist()
    classes = r.boxes.cls.tolist()
    confs = r.boxes.conf.tolist()
    tracks = []
    for i in range(len(ids)):
        tracks.append({"track_id": int(ids[i]), "box": tuple(boxes[i]),
                       "class_id": int(classes[i]), "confidence": float(confs[i])})
    return tracks
