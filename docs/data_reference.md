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
| `counter_state` | `make_counter_state` (built) | dict | see below |
| `speed_state` | `make_speed_state` (built) | dict | see below |
| `class_of` | `process_video` (built) | dict | `{track_id: class_id}`, e.g. `{7: 2, 12: 7}` |
| `speed_lists` | `process_video` (built) | dict | `{track_id: [every speed measured]}`, e.g. `{7: [81.0, 80.6]}` |

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
| `frame_idx` | `process_video` | int | `41`, frame number in the FULL video (starts at `start_frame`, not 0, when a range is given) |
| `tracks` | `track_frame` (built) | list of dicts | see below |
| `t` | `for t in tracks` | dict | one vehicle from `tracks` |
| `speeds` | `update_speeds` (built) | dict | `{7: 81.0}`, speeds this frame only |

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
| `reference_point(box)` | built | tuple, pixels | `(859.05, 702.3)`, bottom-center of the box |
| `to_meters(H, x, y)` | built | tuple, meters | `(2.0, 7.25)` |
| `prev`, `curr` | `update_counts` (built) | tuple, pixels | last frame's and this frame's reference point |

## Output of `process_video` (built)

```python
{
    "model": "yolo26n.pt",
    "frames_processed": 1800,
    "fps": 30.0,                          # the video's frame rate
    "processing_fps": 45.2,               # how fast the program ran
    "start_frame": 1800,                  # first frame processed
    "end_frame": 3600,                    # last frame processed + 1
    "counts": {"positive": 214, "negative": 0},
    "vehicles": [
        {"track_id": 7, "class": "car", "speed_kmh": 81.2, "counted": True},
        {"track_id": 9, "class": "car", "speed_kmh": None, "counted": True},    # crossed, no speed
        {"track_id": 12, "class": "truck", "speed_kmh": 74.0, "counted": False}, # speed, did not cross
    ],
}
```

Class names: `{2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}`.

`vehicles` holds every track that crossed the line OR got at least one speed, sorted by ID. `speed_kmh` is the mean of that track's `speed_lists` entry, rounded to 0.1.

## Output of `run_benchmark` (built, Layer 7)

One dict per model in `MODELS`, in order n, s, m:

```python
{
    "model": "yolo26n.pt",
    "frames_processed": 1800,
    "start_frame": 1800,
    "end_frame": 3600,
    "counts": {"positive": 214, "negative": 0},      # program
    "count_error_pct": {
        "positive": 1.4,      # percent_error(program +, hand +); None if hand + is 0
        "negative": None,     # percent_error(program -, hand -); None if hand - is 0
        "total": 1.4,         # sum of the ones that are not None
    },
    "processing_fps": 55.6,
    "speed_errors": None,     # {"mae_kmh", "bias_kmh", "mape_pct"} when speed clips were used
    "speed_clips_used": [],   # paths of speed clips with exactly 1 vehicle
}
```

`metrics.percent_error(measured, truth)`: number, or None when `truth == 0`.
`metrics.speed_errors(predicted, truth)`: `{"mae_kmh": 2.0, "bias_kmh": 0.0, "mape_pct": 4.0}`. Bias > 0 means speeds read high.
