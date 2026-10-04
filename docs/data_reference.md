# Data reference

What each variable in the finished pipeline holds. Example values are made up for illustration.
Functions marked "planned" follow CLAUDE.md and are not built yet; update this file if they change.

**`state` is a parameter name.** Inside `update_counts` it refers to `counter_state`. Inside `update_speeds` it refers to `speed_state`.

## Inputs (fixed, from `config.py`)

| Name | Type | Example | Meaning |
|---|---|---|---|
| `SRC` / `src` | array (21, 2) | `[[763.8, 1031.4], ...]` | calibration points in pixels |
| `DST` / `dst` | array (21, 2) | `[[3.6576, 0.0], ...]` | the same points in meters |
| `LINE_A`, `LINE_B` / `line_a`, `line_b` | tuple | `(1735.0, 975.1)` | ends of the counting line, in pixels |
| `ZONE` / `zone` | tuple | `(-4.7, 14.8, 0.0, 27.4)` | speed zone `(x_min, x_max, y_min, y_max)` in meters |
| `window` | int | `10` | compare positions this many entries apart |

## Created once, before the frame loop

| Name | Made by | Type | What's inside |
|---|---|---|---|
| `cap` | `open_video` (built) | OpenCV object | hands out frames with `cap.read()` |
| `fps` | `open_video` (built) | float | `30.0`, the video's frame rate |
| `H` | `build_homography` (built) | array (3, 3) | pixel to meter matrix |
| `tracker` | `make_tracker` (built) | YOLO model | detects and tracks; remembers vehicles between frames |
| `counter_state` | `make_counter_state` (planned) | dict | see below |
| `speed_state` | `make_speed_state` (planned) | dict | see below |
| `class_of` | `process_video` (planned) | dict | `{track_id: class_id}`, e.g. `{7: 2, 12: 7}` |
| `speed_lists` | `process_video` (planned) | dict | `{track_id: [every speed measured]}`, e.g. `{7: [81.0, 80.6]}` |

`counter_state` (called `state` inside `update_counts`):

```python
{
    "last_point":  {7: (850.2, 702.3), 12: (1255.1, 770.0)},   # each ID's point last frame, in pixels
    "counted_ids": {7},                                        # IDs already counted (a set)
    "counts":      {"positive": 1, "negative": 0},            # running totals
}
```

`speed_state` (called `state` inside `update_speeds`):

```python
{
    "positions": {
        7: [(40, 2.0, 5.00), (41, 2.0, 5.75), ...],   # (frame_idx, X, Y), X and Y in meters
        12: [...],
    }
}
```

## Created every frame

| Name | Made by | Type | Example |
|---|---|---|---|
| `frame` | `cap.read()` | array (1080, 1920, 3), uint8, BGR | the image |
| `frame_idx` | `process_video` | int | `41`, frame number starting at 0 |
| `tracks` | `track_frame` (built) | list of dicts | see below |
| `t` | `for t in tracks` | dict | one vehicle from `tracks` |
| `speeds` | `update_speeds` (planned) | dict | `{7: 81.0}`, speeds this frame only |

`tracks`:

```python
[
    {"track_id": 7,  "box": (812.4, 640.1, 905.7, 702.3), "class_id": 2, "confidence": 0.56},
    {"track_id": 12, "box": (1200.0, 700.5, 1310.2, 770.0), "class_id": 7, "confidence": 0.81},
]
```

Layer 2's `detect` (built) returns the same shape without `"track_id"`. Track IDs are not numbered 1, 2, 3 in order: they jump (e.g. 1, 6, 7, 23, 108), and may not start at 1.

## Values computed from one vehicle

| Name | Made by | Type | Example |
|---|---|---|---|
| `reference_point(box)` | planned | tuple, pixels | `(859.05, 702.3)`, bottom-center of the box |
| `to_meters(H, x, y)` | built | tuple, meters | `(2.0, 7.25)` |
| `prev`, `curr` | `update_counts` (planned) | tuple, pixels | last frame's and this frame's reference point |

## Output of `process_video` (planned)

```python
{
    "model": "yolo26n.pt",
    "frames_processed": 3622,
    "fps": 30.0,                          # the video's frame rate
    "processing_fps": 45.2,               # how fast the program ran
    "counts": {"positive": 214, "negative": 0},
    "vehicles": [{"track_id": 7, "class": "car", "speed_kmh": 81.2}, ...],
}
```

Class names: `{2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}`.
