from ultralytics import YOLO

model = YOLO("yolo26n.pt")  # loaded once, when this file is imported


def detect(frame):
    """Detect vehicles in one frame. Returns a list of {"box", "class_id", "confidence"} dicts."""
    r = model(frame, conf=0.3, iou=0.5, classes=[2, 3, 5, 7], verbose=False)[0]
    detections = []
    for box, cls, conf in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist()):
        detections.append({"box": tuple(box), "class_id": int(cls), "confidence": float(conf)})
    return detections
