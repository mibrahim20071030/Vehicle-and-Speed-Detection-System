import cv2

LINE_COLOR = (0, 255, 0)  # green (BGR)
BOX_COLOR = (0, 0, 255)  # red (BGR)
COUNTS_COLOR = (0, 0, 255)  # red (BGR), counts title and numbers
COUNTS_SCALE = 1.2
LABEL_COLOR = (0, 255, 255)  # yellow (BGR), track ID and speed text
LABEL_BG_COLOR = (0, 0, 0)  # black (BGR), filled box behind the label
LABEL_SCALE = 0.9


def open_video(path):
    """Open a video file. Returns (cap, fps), where fps is the video's frame rate."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("Could not open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    return cap, fps


def draw_overlay(frame, line_a, line_b, tracks=(), counts=None, speeds=None):
    """Return a copy of frame with the counting line, track boxes, labels and counts drawn on it."""
    out = frame.copy()
    cv2.line(out, (int(line_a[0]), int(line_a[1])), (int(line_b[0]), int(line_b[1])), LINE_COLOR, 2)

    for t in tracks:
        x1, y1, x2, y2 = (int(v) for v in t["box"])
        cv2.rectangle(out, (x1, y1), (x2, y2), BOX_COLOR, 2)

        track_id = t.get("track_id")
        parts = []
        if track_id is not None:
            parts.append(f"ID {track_id}")
            if speeds and track_id in speeds:
                parts.append(f"{speeds[track_id]:.1f} km/h")
        if parts:
            label = " ".join(parts)
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, LABEL_SCALE, 2)
            ty = max(y1 - 6, th + 6)  # text baseline; kept inside the frame at the top edge
            cv2.rectangle(out, (x1, ty - th - 4), (x1 + tw + 4, ty + baseline), LABEL_BG_COLOR, -1)
            cv2.putText(out, label, (x1 + 2, ty), cv2.FONT_HERSHEY_SIMPLEX, LABEL_SCALE, LABEL_COLOR, 2)

    if counts is not None:
        # "Counts" title with the totals under it, in the top-right corner on a black box
        lines = ["Counts", f"+: {counts['positive']}  -: {counts['negative']}"]
        sizes = [cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, COUNTS_SCALE, 2)[0] for text in lines]
        box_w = max(w for w, _ in sizes) + 20
        line_h = max(h for _, h in sizes) + 14
        x0 = max(out.shape[1] - box_w - 10, 0)
        cv2.rectangle(out, (x0, 10), (x0 + box_w, 10 + line_h * len(lines) + 6), LABEL_BG_COLOR, -1)
        for i, text in enumerate(lines):
            cv2.putText(out, text, (x0 + 10, 10 + line_h * (i + 1)), cv2.FONT_HERSHEY_SIMPLEX,
                        COUNTS_SCALE, COUNTS_COLOR, 2)

    return out
