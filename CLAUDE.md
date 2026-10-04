# CLAUDE.md: Project 1, Vehicle Counting + Speed Estimation

## Goal

A program that reads video from a fixed camera, detects vehicles (YOLO via Ultralytics), tracks them (ByteTrack), counts line crossings per direction, and estimates each vehicle's speed using a homography calibrated from known real-world distances. A FastAPI endpoint wraps it.

End product: GitHub repo, demo GIF, working API endpoint, README with counting accuracy, speed error, calibration error, and FPS for YOLO nano, small, and medium.

## How to work in this repo

- Build one layer at a time, in order. A layer is done only when its tests pass AND all earlier layers' tests still pass.
- Run `pytest` from the repo root after every change.
- Logic goes in functions with plain inputs and plain outputs (numbers, tuples, lists, dicts). Code that touches video files or the model stays thin.
- Keep the function names and signatures in this file. If one must change, update this file in the same change.
- Mark every placeholder value with a `# MADE-UP` comment until it is replaced with a real measurement.
- Mark every value that rests on an unverified assumption (for example a road-marking standard) with `# ASSUMED`. `# MADE-UP` is only for placeholders.

## How to explain code to me

- When code calls a function defined in this project, show that function next to the explanation and mark it **(ours)**. Anything not marked is built into Python or a library.
- Define every variable before using it in an explanation.
- No analogies. Plain, direct explanations.

## Conventions

- Points are `(x, y)`: x = column, y = row. y grows DOWNWARD. Origin is the top-left pixel.
- Arrays are indexed `frame[row, col]` = `frame[y, x]`. Frame shape is `(height, width, 3)`, dtype `uint8`.
- OpenCV drawing takes `(x, y)` points. `cv2.VideoWriter` takes size as `(width, height)`.
- Colors are BGR: `(0, 255, 0)` is green, `(0, 0, 255)` is red.
- Boxes are `(x1, y1, x2, y2)` in pixels: top-left and bottom-right, so `x1 < x2` and `y1 < y2`.
- Reference point of a vehicle = bottom-center of its box: `((x1 + x2) / 2, y2)`. Used for BOTH counting and speed.
- Road positions are `(X, Y)` in meters. The origin is whatever `DST` sets.
- Time between two entries = `(frame1 - frame0) / fps`, using the VIDEO's fps. Never use the computer's clock for speed.
- Speeds are reported in km/h (m/s x 3.6).
- COCO vehicle class IDs: 2 car, 3 motorcycle, 5 bus, 7 truck.
- Counts are `{"positive": n, "negative": m}`: which side of the line from A to B the vehicle ended on. The README must say what each means on screen for the footage used. Swapping A and B swaps them.

## Repo layout

```
calibration_points.json  source of truth for SRC, DST, LINE_A, LINE_B, ZONE (do not edit point values by hand)
calibration_overlay.png  reference picture of frame 0 with grid, points, line, zone
config.py          camera setup: loads SRC, DST, LINE_A, LINE_B, ZONE, FRAME_SIZE from calibration_points.json
footage/           real clips (from Pexels), annotated_demo.mp4, count_60_120.mp4; layer_checks/ holds the Layer 1 to 5 check videos L1_counting_line, L2_detection_boxes, L3_tracking_ids, L4_line_counts, L5_speeds (all videos git-ignored by footage/**/*.mp4)
tools/             one-off scripts, not part of the pipeline: click_points.py, draw_calibration.py, calibration_report.py
docs/              data_reference.md (what each pipeline variable holds; update when a layer changes it), calibration.md (calibration details for readers; linked from the README)
scripts/           annotate_line.py (Layer 1 manual check; with [start_s] [end_s] it adds a time/frame stamp, used for the Layer 7 hand-count video), annotate_detections.py (Layer 2 visual check), annotate_tracks.py (Layer 3 visual check), make_demo.py (Layer 6: annotated video + demo.gif)
pytest.ini         puts the repo root on the import path for tests
video.py           Layer 1: open_video, draw_overlay
detector.py        Layer 2: detect
tracker.py         Layer 3: make_tracker, track_frame
counting.py        Layer 4: iou, side_of_line, crossed, reference_point, make_counter_state, update_counts
calibration.py     Layer 5: build_homography, to_meters, check_calibration
speed.py           Layer 5: speed_kmh, make_speed_state, update_speeds
pipeline.py        Layer 6: process_video
main.py            Layer 6: FastAPI app
metrics.py         Layer 7: percent_error, speed_errors
benchmark.py       Layer 7: run_benchmark
tests/
  helpers.py       make_video (shared test helper)
  data/            car.jpg, one_car.mp4 (both cut from the calibration clip, Pexels; no identifiable people)
  test_video.py, test_detector.py, test_tracker.py, test_counting.py,
  test_speed.py, test_calibration_config.py, test_api.py, test_metrics.py
README.md
```

Do not add `tests/__init__.py` (tests import `helpers` by plain name).

## Dependencies

`ultralytics`, `opencv-python`, `numpy`, `fastapi`, `uvicorn`, `python-multipart` (needed for file uploads), `pytest`, `httpx` (needed for FastAPI's TestClient).

Model weights: `yolo26n.pt`, `yolo26s.pt`, `yolo26m.pt` (YOLO26, the current Ultralytics family in ultralytics 8.4.172; chosen 2026-10-03). Use the same family for all three sizes. Checked 2026-10-03: `iou=` still changes the number of boxes for YOLO26 (7 / 10 / 19 boxes at iou 0.1 / 0.5 / 0.9 on frame 0), so NMS still runs and `iou=0.5` stays.

---

## Scene

- Calibration clip: `footage/Untitled design.mp4` (file name has a space), 1920 x 1080, 30 fps, **5557 frames (185.2 s)**. Evening, dusk, near LaGuardia Airport.
  - Replaced 2026-10-04 by the user with a 1920 x 1080 export of the full 3-minute clip, under the same file name. The earlier file (3622 frames, about 2 minutes, a trimmed copy) is gone. Layers 1 to 5 checks and `tests/data/*` were made from the earlier file.
  - Checked: frame 0 of the new file is identical to the old frame 0 (`tests/data/car.jpg`): 0.0 px shift on the horizon band and the road, mean pixel difference 0.84 (JPEG). The calibration is valid on frame 0.
  - Late frames (60, 110, 150, 184 s, by eye): the road sits higher in the frame than the calibration points, as described in the drift note below. The shift at 150 s and 184 s looks about the same as at 110 s, not larger. The counting line still spans the near lanes.
- Second file: `footage/original_3min.mp4`, 3840 x 2160, 29.97 fps, 5552 frames. The same 3 minutes at 4K. No longer needed (the 1080p export replaces it); the calibration does not fit it.
- Elevated, oblique side view of a divided highway. A concrete median barrier separates the **near carriageway** (5 lanes; traffic appears to move left to right in the image, judging by the tail lights) from the far carriageway.
- **Count and measure speed on the near carriageway only.** Far-lane vehicles are small and partly hidden by the barrier, and they map outside the speed zone.
- The camera is **not perfectly fixed**. Measured against frame 0 (far horizon band): about -18 px shift at 10 s, -33 px at 17 s, -47 px at 90 s, -68 px at 110 s, with about 1 to 2% scale change. Stabilization is optional (see "Optional later: stabilization").
  - Measured at the ROAD near the counting line (2026-10-04, 185 s export, median of 9 frames per time to remove cars, only readings with match score >= 0.8 trusted; rough): the dashes move from 0 to about -50 px in x during 0 to 35 s, stay at about -51 to -58 px from 35 to 95 s, move between about -35 and -85 px from 100 to 145 s, and are back near -50 to -60 px at 160 to 180 s. y moves only a few px. No 2-minute stretch is stable, and no stretch after the first seconds lines up with the frame-0 calibration.
  - Decided 2026-10-04 (user): accept the drift, no stabilization for now. State it as a limitation in the README. Add stabilization only if the hand count shows missed lane 5 vehicles.
- All pixel coordinates are in **original 1920 x 1080 frame pixels**. Do not crop or resize frames before detection or tracking. Ultralytics resizes internally and returns boxes in original coordinates.
- No people visible. Source: Pexels (Pexels license, free to use). The README must name the source and license.

## Calibration decisions (also record in the README)

**Source of real distances:** the road's own lane markings, not a measured distance.
- NYSDOT standard broken lane line: 10 ft line + 30 ft gap. One cycle (start of a dash to the start of the next) = 40 ft = **12.192 m**. Dash length = 10 ft = **3.048 m**.
- Lane spacing assumed 12 ft = **3.6576 m** (NYSDOT standard travel lane width).
- Dashes are assumed to start at the same place along the road on every lane line (they appear collinear across lines in the image).
- **None of this is independently verified.** The road may be city-maintained, repainted, or built to a different standard. The README must say so.

**World frame (meters):**
- X across the road: 0 = lane line `a` (the nearest dashed line to the camera), then 3.6576 (`b`), 7.3152 (`c`), 10.9728 (`d`). Increases toward the barrier.
- Y along the road: 0 = the first dash row, 12.192 = second row, 24.384 = third row. Increases to the right in the image.

**Points:** 21 points = dash starts (Y = row x 12.192) and dash ends (Y = row x 12.192 + 3.048) on 4 lane lines x 3 rows. The start of line `a` row 1 is cut off by the bottom of the frame, so only its end is used. Line `d` row 3 is not used. Pixel positions were refined to sub-pixel using intensity profiles along each dash on a vehicle-free median image of frames 0 to 45, and are stored rounded to 0.1 px. They are valid for **frame 0 of the calibration clip** (within about 2 px). The full list is in `calibration_points.json`.

**Counting line (pixels):** a real cross-road line at Y = 12.192 m (the row 2 dashes), from X = -4.6 m (just beyond the right edge line) to X = 15.4 m (just beyond the barrier-side lane edge):
- `LINE_A = (1735.0, 975.1)` (right end, near the edge line)
- `LINE_B = (809.8, 861.3)` (left end, near the barrier)
- With this order of A and B, a vehicle crossing **left to right** (increasing Y) lands on the **positive** side. So `counts["positive"]` = vehicles moving left to right, `counts["negative"]` = right to left. The README must say this.

**Speed zone (meters, `ZONE = (x_min, x_max, y_min, y_max)`):** `(-4.7, 14.8, 0.0, 27.4)`. Covers the 5 near lanes over the calibrated stretch. Far-lane pixels map outside it. The zone stops at Y = 27.4 m because error grows when extrapolating beyond the calibrated rows (see the held-out test below).

**Calibration report baseline** (`tools/calibration_report.py`, H from all 21 points). These come from the rounded JSON values; they replace the slightly different numbers first given (2.78 / 4.96 px, 0.167 / 0.381 m), which came from unrounded pixels.

| Quantity | Baseline |
|---|---|
| Pixel reprojection error, RMS / max | 2.78 px / 4.98 px |
| Position error in meters when converting the 21 pixels, RMS / max | 0.164 m / 0.370 m |
| Held-out test: fit with rows 1 and 2 only, predict row 3 (not used in the fit), mean error | about 0.35 m (range 0.17 to 0.67 m) |
| Held-out test: predicted row 2 to row 3 spacing on lines a, b, c (true value 12.19 m) | about 12.16, 12.50, 12.78 m |
| Edge line check: solid right edge line should have constant X. Pixels (1503, 1080), (1657, 1004), (1825, 920) | X about -4.40, -4.39, -4.33 m |

These are consistency checks. They use the same lane-marking assumption, so they do NOT verify the absolute scale.

---

## Layer 1: read video and draw

**File:** `video.py`

**Functions:**
- `open_video(path)` returns `(cap, fps)`. Raises `ValueError("Could not open video")` if `cap.isOpened()` is False. `fps = cap.get(cv2.CAP_PROP_FPS)`.
- `draw_overlay(frame, line_a, line_b, tracks=(), counts=None, speeds=None)` returns a NEW frame. Works on `frame.copy()` so the original is never changed. Draws:
  - the counting line from `line_a` to `line_b`, green, thickness 2
  - for each track: its box (thickness 2) and a label with `track_id` (use `t.get("track_id")`, since Layer 2 detections have none) and speed from `speeds` if present
  - if `counts` is given: a "Counts" title with `+: n  -: m` under it, in the top-right corner, red, scale 1.2, on a filled black box (changed 2026-10-04 at the user's request; was plain text in the top-left)
  - track labels in yellow, scale 0.9, on a filled black box (changed 2026-10-04 at the user's request)
  - box corners converted to `int` before drawing

**Test helper (`tests/helpers.py`):**
- `make_video(path, n_frames=10, w=64, h=48, fps=10)`: writes `n_frames` frames with `cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))`. Frame `i` is `np.full((h, w, 3), i * 10, dtype=np.uint8)`. If `mp4v` fails on this machine, choose another codec and note it here.

**Tests (`tests/test_video.py`):**
- `test_read_video`: make a 10-frame video in `tmp_path`, read it back with `open_video` and the read loop. Assert 10 frames, each shape `(48, 64, 3)`. Do not assert pixel values (compression changes them).
- `test_open_video_bad_path`: `open_video("missing.mp4")` raises `ValueError`.
- `test_draw_overlay_draws_line_on_copy`: black frame `np.zeros((100, 200, 3), np.uint8)`, line from `(10, 50)` to `(190, 50)`. The returned frame has `[0, 255, 0]` at `[50, 100]` (row 50, column 100). The original frame is still all zeros.

**Done when:** tests pass, and a small script reads a real clip and writes an annotated copy showing the counting line.

---

## Layer 2: detection

**File:** `detector.py`

**Module level:** `model = YOLO("yolo26n.pt")`, loaded once when the file is imported.

**Function:**
- `detect(frame)` returns a list of dicts: `{"box": (x1, y1, x2, y2), "class_id": int, "confidence": float}`. Uses `model(frame, conf=0.3, iou=0.5, classes=[2, 3, 5, 7], verbose=False)[0]`. Empty list when nothing is found.

**Tests (`tests/test_detector.py`):**
- `test_detect_returns_vehicles`: `cv2.imread("tests/data/car.jpg")`, assert it is not None. Assert at least 1 detection. For every detection: `class_id in (2, 3, 5, 7)`, `0 <= confidence <= 1`, `x1 < x2` and `y1 < y2`. Do NOT assert exact coordinates (they shift between model and library versions).
- `test_detect_blank_frame`: `detect(np.zeros((480, 640, 3), np.uint8))` returns `[]`.

**Done when:** tests pass, and boxes drawn with `draw_overlay` on a real clip look right by eye.

---

## Layer 3: tracking

**File:** `tracker.py`

**Functions:**
- `make_tracker(model_name="yolo26n.pt")` returns a NEW `YOLO(model_name)`. Call once per video. The tracker keeps state between calls, so never share one across videos, and keep it separate from `detector.model`.
- `track_frame(tracker_model, frame)` returns a list of dicts: `{"track_id": int, "box": (x1, y1, x2, y2), "class_id": int, "confidence": float}`. Uses `tracker_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.1, iou=0.5, classes=[2, 3, 5, 7], agnostic_nms=True, verbose=False)[0]`. Returns `[]` when `r.boxes.id is None`. Pairs IDs with boxes by index `i`.
  - `agnostic_nms=True` added 2026-10-04 (Layer 7, user agreed): without it, duplicate boxes are merged only within one class, so a van labeled both car and truck kept two boxes, got two IDs and was counted twice (yolo26s / m only). Confirmed and tested on the tuning minute 0 to 60 s first: double counts n / s / m 0 / 3 / 6 before, 0 / 0 / 0 after. `detector.detect` is unchanged (only used for the Layer 2 check).

**Tests (`tests/test_tracker.py`):**
- `test_one_vehicle_keeps_one_id`: on `tests/data/one_car.mp4`, count how often each track ID appears with `collections.Counter`. Assert at least one frame had tracks, and the most common ID appears in at least 80% of frames that had tracks. Do not assume IDs start at 1.
  - `one_car.mp4` is NOT 5 s: it is frames 2230 to 2264 of `footage/Untitled design.mp4` (35 frames, 1.17 s at 30 fps), cropped to x 220 to 1020, y 630 to 1080 (800 x 450). One dark minivan on the far carriageway, near lanes empty. A 5 s single-vehicle clip does not exist in this footage: traffic is dense and a car crosses a fixed crop in about 1.5 s (searched all 3622 frames, 2026-10-04). Checked: `detect` at conf 0.1 finds exactly 1 box in every frame of the crop.
  - 80% kept: the minivan has ID 1 in 35 of 35 frames (100%).
- `test_blank_frames_have_no_tracks`: 3 black frames through one tracker each return `[]`.

**Verified 2026-10-04 (ultralytics 8.4.172):**
- `bytetrack.yaml` defaults: `track_high_thresh 0.25`, `track_low_thresh 0.1`, `new_track_thresh 0.25`, `track_buffer 30`, `match_thresh 0.8`, `fuse_score True`. `conf=0.1` equals the low threshold, so round 2 gets boxes. New IDs start only from boxes with score >= 0.25.
- Reset without reloading: `tracker_model.predictor.trackers[0].reset()` (clears tracks, Kalman filter, and the ID counter). `predictor` exists only after the first `.track()` call. Not used yet.
- The ID counter is shared by all trackers in one Python process, so a second tracker's IDs may not start at 1.

**Visual check** (`scripts/annotate_tracks.py`, first 300 frames): 67 IDs, 20 of them ever inside ZONE. Near-lane tracks mostly keep one ID from the left edge to the right edge. Known failure: a car in lane 5 (barrier side) hidden behind a nearer car loses its box and is not picked up again (IDs 6 and 227; 227 was lost right at the counting line at frame 140). Such a car can be missed by the counter.

---

## Layer 4: line counting

**File:** `counting.py`

**Functions:**
- `iou(a, b)`: overlap edges are `max` of the two left/top edges and `min` of the two right/bottom edges. `inter = max(0, ox2 - ox1) * max(0, oy2 - oy1)`. Returns `inter / (area_a + area_b - inter)`.
- `side_of_line(a, b, p) = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])`. Only the sign matters.
- `crossed(a, b, prev, curr)`: `s1, s2` = sides of `prev`, `curr` relative to line a-b. `t1, t2` = sides of `a`, `b` relative to path prev-curr. Returns `(s1 * s2 < 0) and (t1 * t2 < 0)`.
- `reference_point(box)` returns `((x1 + x2) / 2, y2)`.
- `make_counter_state()` returns `{"last_point": {}, "counted_ids": set(), "counts": {"positive": 0, "negative": 0}}`.
- `update_counts(state, tracks, a, b)`: for each track, compare `reference_point(box)` with `state["last_point"].get(track_id)`. If there is a previous point, the ID is not yet counted, and `crossed(...)` is True: add the ID to `counted_ids` and add 1 to `"positive"` if `side_of_line(a, b, curr) > 0`, else `"negative"`. Always save the current point to `last_point`. Changes `state` in place, returns nothing.

**Tests (`tests/test_counting.py`),** with `A, B = (100, 300), (800, 300)` and helper `make_track(track_id, cx, bottom_y)` building box `(cx - 20, bottom_y - 40, cx + 20, bottom_y)`:
- `test_iou`: `(0,0,10,10)` vs `(5,0,15,10)` is 1/3. Identical boxes give 1.0. `(0,0,10,10)` vs `(20,0,30,10)` gives 0.
- `test_crossing_detected`: `crossed(A, B, (400, 297), (400, 305))` is truthy.
- `test_no_crossing_same_side`: `crossed(A, B, (400, 290), (400, 297))` is falsy.
- `test_path_beyond_line_end_not_counted`: `crossed(A, B, (900, 297), (900, 305))` is falsy.
- `test_vehicle_counted_once_going_down`: bottom_y sequence `[280, 290, 297, 305, 315, 295, 310]` for ID 1 gives counts `{"positive": 1, "negative": 0}`.
- `test_vehicle_going_up_counts_negative`: `[320, 310, 303, 295, 285]` gives `{"positive": 0, "negative": 1}`.
- `test_first_frame_never_counts`: one frame only gives zeros.

Use `assert crossed(...)` / `assert not crossed(...)`, not `is True` (NumPy booleans fail `is True`).

**Known limit:** a reference point exactly on the line (side = 0) is not counted for that step. Rare with decimal coordinates.

**Known limit (seen 2026-10-04):** a vehicle that loses its track before its reference point crosses the line is never counted. Example: car 227 (lane 5, barrier side) goes behind a nearer car at frame 140; its last point (982, 892) is still on the negative side, so it is missed. The user chose to deal with this later (check its effect in the hand count). Layer 6 run on the 185 s export (2026-10-04): the same car (now ID 246) WAS counted. Its confidence drops to 0.24 at frame 141, it crosses at frame 142, and its track is lost at frame 143. A 1-frame margin, so the limit still applies. Vehicles already past the line at frame 0 (IDs 1, 6, 7) are also not counted, because the first frame never counts.

**Real-footage check (2026-10-04, first 300 frames, yolo26n):** program 15 positive, 0 negative. **User's hand count: 16** (all left to right). The one missed car is car 227, which goes behind the blue car (ID 221) just before the line. All 15 counted IDs are real crossings (no false counts). This is a 10 s spot check, not the benchmark hand count (Layer 7).

**Built early:** `side_of_line` was built before Layers 2 to 4 for the calibration work (`tests/test_calibration_config.py` uses it). The rest of `counting.py` is still built in Layer 4.

---

## Layer 5: homography and speed

**Files:** `calibration.py`, `speed.py`

**Functions:**
- `build_homography(src, dst)` returns `H`, the pixel-to-meter homography, shape `(3, 3)`. `src` (pixels) and `dst` (meters) are float arrays of shape `(N, 2)` with N >= 4, in the SAME order. No 3 points on one line. Points must be on the road surface.
  - Implementation: `H_m2p, _ = cv2.findHomography(dst, src, 0)`, then `H = np.linalg.inv(H_m2p)` and `H = H / H[2, 2]`.
  - Raises `ValueError` if shapes are wrong, N < 4, or `findHomography` returns None.
  - **Why this direction:** fitting meters-to-pixels minimizes the error in pixels, which is where the measurement noise is. On our data this gives a pixel RMS of 2.78 px. Fitting pixels-to-meters directly and inverting gave 4.04 px RMS.
  - (Replaces the earlier 4-point `cv2.getPerspectiveTransform(src, dst)` version.)
- `to_meters(H, x, y)`: `a, b, w = H @ np.array([x, y, 1.0])`, returns `(a / w, b / w)`.
- `check_calibration(H, pixel_a, pixel_b, known_m)` returns `(measured_m, percent_error)` for two road points NOT used to build H.
- `speed_kmh(p0, p1, frame0, frame1, fps)` returns `math.dist(p0, p1) / ((frame1 - frame0) / fps) * 3.6`.
- `make_speed_state()` returns `{"positions": {}}`.
- `update_speeds(state, tracks, H, frame_idx, fps, window=10, zone=None)`: for each track, convert `reference_point(box)` with `to_meters`. If `zone = (x_min, x_max, y_min, y_max)` is given and the point is outside it, skip that track this frame. Otherwise append `(frame_idx, X, Y)` to that track's list (`setdefault`). If the list has more than `window` entries, speed = `speed_kmh` between entry `[-1 - window]` and `[-1]`, using their stored frame numbers. Returns `{track_id: km/h}` for tracks with enough history.

**Tests (`tests/test_speed.py`):**
- `test_calibration_points_map_to_destination`: **REWRITTEN.** Uses the 4-point case SRC `[[0,0],[100,0],[100,100],[0,100]]`, DST `[[0,0],[1,0],[1,1],[0,1]]` (4 points fit exactly). Each `to_meters(H, *src[i])` is within 0.001 of `dst[i]`. It previously used the `config.py` SRC/DST, but with 21 points the least-squares fit is not exact (0 of 21 points within 0.001 m), so the 21-point check moved to `test_fit_quality` in `tests/test_calibration_config.py`.
- `test_check_calibration_known_scale`: SRC `[[0,0],[100,0],[100,100],[0,100]]`, DST `[[0,0],[1,0],[1,1],[0,1]]`. Pixels `(0,0)` to `(300,400)` measure 5.0 m, error about 0%.
- `test_speed_kmh_345`: `speed_kmh((0,0), (3,4), 0, 30, 30)` is 18.
- `test_speed_kmh_36`: `speed_kmh((0,0), (0,5), 0, 15, 30)` is 36.
- `test_update_speeds_constant_motion`: `H = np.eye(3)` (pixels act as meters), ID 1 with bottom_y `100 + frame_idx` for frames 0..12, `fps=10`, `window=10`. Returns `{}` for frames 0..9, and 36 km/h at the end.
- `test_update_speeds_outside_zone`: same motion with `zone=(0, 1000, 0, 50)` always returns `{}`.

**Manual check (record in README):** on real footage, measure one road distance not used for H, run `check_calibration`, record the percent error. For the current clip, the held-out row 3 test in `tools/calibration_report.py` serves this purpose (it uses the same lane-marking assumption, so it is a consistency check only).

**Built early:** `build_homography` and `to_meters` were built before Layers 2 to 4 for the calibration work. `check_calibration` and all of `speed.py` were built in Layer 5 (2026-10-04).

**Real-footage check (2026-10-04, first 300 frames, yolo26n, window 10, ZONE on):** 19 tracks got a speed. Mean speed per track 57 to 101 km/h (median 81). Within one track, single readings spread about +-10 to 15 km/h around its mean (a 10-frame window is 0.33 s, so box jitter of a few pixels shows up). Tracks with only 2 to 6 readings (IDs 1, 7, 227, 569: at the zone edge at the start/end of the 300 frames, or lost) are the least reliable. Estimates only; no independent ground truth.

**Tests (`tests/test_calibration_config.py`):**

```python
import numpy as np
from calibration import build_homography, to_meters      # (ours)
from counting import side_of_line                         # (ours)
from config import SRC, DST, LINE_A, LINE_B, ZONE

def _in_zone(x, y):
    return ZONE[0] <= x <= ZONE[1] and ZONE[2] <= y <= ZONE[3]

def test_config_shapes():
    assert SRC.shape == DST.shape and SRC.shape[1] == 2 and len(SRC) == 21

def test_fit_quality():
    H = build_homography(SRC, DST)
    errs = [np.linalg.norm(np.array(to_meters(H, *p)) - w) for p, w in zip(SRC, DST)]
    assert np.sqrt(np.mean(np.square(errs))) < 0.25
    assert max(errs) < 0.5

def test_near_lane_pixels_inside_zone():
    H = build_homography(SRC, DST)
    assert _in_zone(*to_meters(H, 900, 960))      # near lane
    assert _in_zone(*to_meters(H, 1500, 930))     # near lane

def test_far_lane_and_edge_pixels_outside_zone():
    H = build_homography(SRC, DST)
    for p in [(1000, 800), (600, 790), (100, 850), (1400, 790)]:
        assert not _in_zone(*to_meters(H, *p))

def test_line_inside_frame():
    for p in (LINE_A, LINE_B):
        assert 0 <= p[0] < 1920 and 0 <= p[1] < 1080

def test_positive_direction_is_left_to_right():
    # a point after the line (larger Y) must be on the positive side
    after = (1518.0, 853.5)      # line b, row 3 start (Y = 24.38)
    before = (763.8, 1031.4)     # line b, row 1 start (Y = 0)
    assert side_of_line(LINE_A, LINE_B, after) > 0
    assert side_of_line(LINE_A, LINE_B, before) < 0
```

---

## Layer 6: pipeline and API

**`config.py`:** loads the numbers from `calibration_points.json` so they are not copied by hand:

```python
_DATA = json.loads((Path(__file__).parent / "calibration_points.json").read_text())

SRC = np.array([p["pixel"] for p in _DATA["points"]], dtype=np.float32)    # pixels, shape (21, 2)
DST = np.array([p["meters"] for p in _DATA["points"]], dtype=np.float32)   # meters, shape (21, 2)  # ASSUMED
LINE_A = tuple(_DATA["line_a"])
LINE_B = tuple(_DATA["line_b"])
ZONE = tuple(_DATA["zone_m"])  # ASSUMED
FRAME_SIZE = tuple(_DATA["frame_size"])
```

The pixel positions are measurements. The meter values rest on the NYSDOT lane-marking standard (not independently verified), so they are `# ASSUMED`, not `# MADE-UP`.

Call `process_video` with `src=SRC, dst=DST, line_a=LINE_A, line_b=LINE_B, zone=ZONE`.

**`pipeline.py`:**
- `process_video(path, src, dst, line_a, line_b, window=10, model_name="yolo26n.pt", zone=None, output_path=None, start_frame=0, end_frame=None)`:
  - Frame range (added 2026-10-04, user's choice over cutting a clip file): only frames `start_frame` to `end_frame - 1` are processed (`end_frame=None` = to the end). Frames before `start_frame` are skipped with `cap.grab()` (exact; seeking in an mp4 can land on the wrong frame). `frame_idx` keeps the full video's numbering, so frame numbers match the hand count. Layer 7 report range: `start_frame=1800, end_frame=3600` (60.0 to 120.0 s).
  - `open_video`, `build_homography`, `make_tracker(model_name)`, `make_counter_state`, `make_speed_state`, all ONCE before the loop.
  - Per frame: `track_frame` then `update_counts` then `update_speeds` then (if `output_path`) `draw_overlay` and write the frame with a `cv2.VideoWriter` sized from the input video's width and height.
  - Keep `class_of[track_id]` and a list of speeds per track. Reported speed per vehicle = average of its list, rounded to 0.1.
  - Timing: start `time.perf_counter()` when `frames_processed == 5` (WARMUP_FRAMES, counted from the first processed frame), at the top of the loop. `processing_fps = (frames_processed - 5) / elapsed`, or `None` if 5 frames or fewer were processed.
  - Returns `{"model", "frames_processed", "fps", "processing_fps", "start_frame", "end_frame", "counts", "vehicles": [{"track_id", "class", "speed_kmh", "counted"}]}`. `end_frame` = last processed frame + 1. Class names from `{2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}` (class of the track's latest frame).
  - `vehicles` (decided 2026-10-04 with the user): every track that crossed the line OR got at least one speed, sorted by ID. `speed_kmh` is `None` for a counted vehicle that never got a speed. `counted` says whether it crossed the line. Far-lane tracks with neither are left out. The annotated video still shows every track.
  - `fps` is the video's rate. `processing_fps` is how fast the program ran. Never mix them.

**`main.py`:**
- `GET /health` returns `{"status": "ok"}`.
- `POST /analyze` with `video: UploadFile = File(...)`: reject extensions other than `.mp4/.avi/.mov` (lowercase compare) with 400. Write the bytes to `tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")`. Call `process_video(path, SRC, DST, LINE_A, LINE_B, zone=ZONE)` inside `try`. Turn `ValueError` into 400. Delete the temp file in `finally`. Return the dict.
- Known trade-offs: the model loads per request (fresh tracker state). Handles one video at a time.

**Tests (`tests/test_api.py`)** using `TestClient(app)` and `make_video` from `helpers`:
- `test_health`: 200 and `{"status": "ok"}`.
- `test_rejects_bad_file_type`: posting `("notes.txt", b"hello", "text/plain")` gives 400.
- `test_rejects_missing_file`: posting with no file gives 422.
- `test_process_video_output_shape`: on the 10-frame gray video: `frames_processed == 10`, counts both 0, `vehicles == []`.
- `test_analyze_small_video`: posting the gray video gives 200 with `counts` and `vehicles` in the JSON.
- `test_process_video_frame_range`: `start_frame=3, end_frame=8` gives `frames_processed == 5`, `start_frame == 3`, `end_frame == 8`, `processing_fps is None`.
- `test_process_video_writes_output`: with `output_path`, the written video has 10 frames.

**Demo GIF:** `python scripts/make_demo.py [start_s] [seconds]` (default 0, 7) runs `process_video` on `footage/Untitled design.mp4` with `output_path=footage/annotated_demo.mp4` (git-ignored), prints the result, and writes `demo.gif` (7.5 fps = every 4th frame so it plays at real speed, 640 px wide, about 4.6 MB; changed 2026-10-04 from 10 s / 10 fps / 9.1 MB so GitHub loads it fast) with Pillow (ffmpeg is not installed on this machine). Footage must have no identifiable people.

**Real-footage check (2026-10-04, first 300 frames, yolo26n):** 16 positive, 0 negative (the Layer 4 run gave 15; the user's hand count is 16). 19 vehicles listed: 16 counted, 3 with a speed but not counted (IDs 1, 7: past the line at frame 0; 522: still before the line at frame 299). Speeds 56 to 101 km/h. Processing 37.9 fps (CPU/GPU of this machine, with video writing). `demo.gif` is 9.1 MB.

---

## Layer 7: benchmark and README

**`metrics.py`:**
- `percent_error(measured, truth)` returns `abs(measured - truth) / truth * 100`, or `None` if `truth == 0`.
- `speed_errors(predicted, truth)` returns `{"mae_kmh", "bias_kmh", "mape_pct"}` from signed errors `predicted - truth`. Every truth value must be above 0.

**`benchmark.py`:**
- `MODELS = ["yolo26n.pt", "yolo26s.pt", "yolo26m.pt"]`.
- `run_benchmark(count_clip, hand_counts, speed_clips, start_frame=0, end_frame=None)`: for each model, run `process_video` on the 1-minute count clip (60 to 120 s, see "Tuning vs reporting split"; the frame range is passed to `process_video`, changed 2026-10-04) (counts and `processing_fps`, no `output_path` so video writing does not slow it) and on each `(clip_path, true_kmh)` speed clip. A vehicle counts for a speed clip if it got a speed; a speed clip is used only if exactly 1 such vehicle is found (track IDs differ between runs, so results can't be matched by ID). Record `speed_clips_used`. Returns one plain dict per model (see `docs/data_reference.md`).
- **Count error (decided 2026-10-04 with the user):** `+ error = percent_error(program +, hand +)`, `- error = percent_error(program -, hand -)`, `Count error = + error + - error`. If the hand count for a direction is 0, that error is `None` (printed `n/a`), the sum uses only the other direction, and a note under the table says so. No other count metric.
- `if __name__ == "__main__":` holds the real clip paths and ground truth, and prints the GPU, CPU, OS and library versions, then a markdown table: Model, Counts (+/-) program vs hand, + error, - error, Count error, Speed MAE, Speed bias, Speed MAPE, FPS. The three speed columns print `n/a` when no speed clips are given. `python benchmark.py --short` runs only 1 s (frames 1800 to 1829) to check the code path; not a result.
- **Current clip has no independent speed ground truth.** Keep the speed-error machinery for a later GPS pass, hallway test, or dataset. The README must say speeds on this clip are estimates only.

**Tests (`tests/test_metrics.py`):**
- `percent_error(105, 100)` and `percent_error(95, 100)` are both 5.0. `percent_error(3, 0)` is None.
- `speed_errors([52, 48], [50, 50])`: MAE 2, bias 0, MAPE 4.

**Ground truth:**
- Counting: hand-count the clip per direction using the SAME definition as the program (bottom-center crosses the line).
- Speed: hallway test (two tape marks a measured distance apart and a stopwatch, repeated several times), phone GPS speed, or a public dataset after checking its terms. Note each method's own error. For a hallway test, confirm early that the test object is detected as class 2, 3, 5, or 7.
- Calibration: one held-out known distance via `check_calibration`.

**Benchmark rules:**
- Same clip, same machine, same settings (`conf`, `iou`, window, calibration, line, zone) for n, s, m. Only the model changes.
- Tune settings on a different clip than the one reported, or state in the README that they were tuned on it.
- Record hardware (CPU/GPU model) and library versions.

**README contains:** demo GIF, what it does, definitions (count, speed, positive/negative meaning), results table for n/s/m, counting ground truth method, speed ground truth method and number of passes, calibration error, limitations, footage source and license, how to run (script, API, tests, benchmark).

**README claims for the current clip:**
- **Counting accuracy:** valid. Hand-count the near carriageway only, per direction, using the same definition as the program (bottom-center of the box crosses the line).
- **FPS for nano, small, medium:** valid.
- **Speed:** *estimates only*. The scale comes from the NYSDOT lane-marking standard (40 ft cycle), not from a measured distance, and no independent speed measurement exists for this clip. Report: calibration residuals, the held-out test, and a sanity check against the posted speed limit (read from Street View).
- **Sensitivity (computed for a vehicle at 90 km/h, 10-frame window):**
  - Lane width assumption: +-10% changes speed by about 0.1 km/h for a vehicle moving along its lane, because speed along the road depends on the dash cycle, not the lane width.
  - Random 2 px error on the calibration points: about +-0.4 km/h.
  - A wrong assumption about the dash cycle length scales every speed by the same percentage (a 3 m / 9 m metric pattern would make true speeds about 1.6% lower than reported).
  - Camera drift, if H is not updated: speeds read about 1% low at 17 s, 1 to 3% high around 60 s, and 1 to 5% high near 110 s.
- **Limits to state:** one dusk clip, near carriageway only, handheld or slightly moving camera, speed not independently validated.
- **Tuning vs reporting split (decided 2026-10-04, replaces the 3 to 5 minute spec):** both parts come from `footage/Untitled design.mp4` (the 185 s export). Tune on 0 to 60 s, report on 60 to 120 s (1 minute). "Tuning" = changing our settings (`conf`, `iou`, `window`, line, zone), never training the model. Results on 60 to 120 s are run once with the final settings. The README must say: both parts come from the same camera and conditions, the reported part is 1 minute, and the camera drifts during it (see Scene). The program gets only 60 to 120 s through `process_video(..., start_frame=1800, end_frame=3600)` (decided in Layer 6).
- **Hand count (done 2026-10-04):** 60 to 120 s, near carriageway, from `footage/count_60_120.mp4`: **83 positive, 0 negative**.
- **Results (2026-10-04, final, with `agnostic_nms=True`, run once):**

| Model | Counts (+/-) | Count error | FPS | Median speed |
|---|---|---|---|---|
| yolo26n | 83 / 0 | 0.0% | 59.1 | 80.6 km/h |
| yolo26s | 83 / 0 | 0.0% | 55.8 | 81.7 km/h |
| yolo26m | 83 / 0 | 0.0% | 45.2 | 81.6 km/h |

  Before the fix (first run): n 83 (58.6 fps), s 85, m 86. Every extra s / m count was one vehicle with two boxes (two IDs crossing in the same frame at the same point; s: frames 1945, 3278; m: 3278, 3479, 3550), mostly car + truck. The README tells this story and says the problem was first noticed on the reported minute. Totals only; no per-car matching against the hand count. Posted limit 50 mph = 80.5 km/h (user, Street View). Calibration report re-run: matches the baseline.
- **Speed error: closed as not possible with this footage (decided 2026-10-04 with the user).** No known-speed test is available (no GPS pass, hallway test or usable dataset). The README reports the median speed against the posted limit as a plausibility check only, never as an error, and says what would be needed to measure it. The speed-error code stays for later.

---

## Tools (scripts, not part of the pipeline)

- `tools/click_points.py <image>`: opens the image with `cv2.imread`, prints the `(x, y)` pixel of each left click (`cv2.EVENT_LBUTTONDOWN`), draws a small green circle there, quits on Esc.
- `tools/draw_calibration.py <video> <out.png>`: reads frame 0, draws the metric grid (lines at X = -1 lane to +4 lanes, rows at Y = 0, 12.192, 24.384), the 21 calibration points, the counting line, and the ZONE polygon. Use it to confirm the numbers still match a clip. It should look like `calibration_overlay.png`.
- `tools/calibration_report.py`: prints the fit quality, the held-out test, and the edge line check (see the baseline table in "Calibration decisions").

---

## Optional later: stabilization

Not built. Do not change `video.py` for this unless it is needed.

The camera drift also moves the counting line relative to the road. By about 110 s, the barrier-side lane edge appears at about X = 16.5 m in the frame-0 calibration, versus 14.6 m at frame 0 (about 1.9 m further). The line ends at X = 15.4, so lane 5 vehicles could be partly missed late in the clip, and speeds drift as described above.

If this shows up in the hand-count comparison, add `stabilize(frame, reference_frame)` in Layer 1: estimate a similarity transform from ORB features in the **far horizon band only** (y between about 560 and 700; static airport buildings and lights) and warp the frame back to the reference with `cv2.warpAffine`. In a test, this reduced the horizon residual to about 1 to 2 px. The near-road residual was noisier (about 1 to 10 px), so verify by drawing the fixed line and calibration points over a few warped frames. Test with a synthetic image shifted by a known amount.

Run the benchmark both with and without stabilization and report the difference.

---

## Open items to verify during the build

- ~~Current Ultralytics model family names.~~ Resolved 2026-10-03: YOLO26.
- ~~`bytetrack.yaml` default thresholds versus the `conf` passed to `.track()`.~~ Resolved 2026-10-04 (see Layer 3).
- ~~A way to reset tracker state without reloading the model.~~ Resolved 2026-10-04 (see Layer 3).
- ~~Whether `mp4v` works for `cv2.VideoWriter` on this machine.~~ Verified 2026-10-03: works (Windows 11, opencv-python 5.0.0, Python 3.14.6).
- Whether the hallway test object is detected as a vehicle class.
- ~~Report clip for the count benchmark.~~ Resolved 2026-10-04: the user replaced `footage/Untitled design.mp4` with a 1920 x 1080 export of the 3-minute clip; frame 0 matches the calibration (see Scene). Earlier note: the calibration does NOT match `footage/original_3min.mp4` at its native 3840 x 2160 (checked 2026-10-03 with `tools/draw_calibration.py`: the grid lands in the sky, top-left quarter). Frame 0 shows the same scene and vehicles as the calibration clip at twice the resolution, so a x2 pixel scale or a downscale to 1920 x 1080 may fit, but neither is verified and the "do not resize" rule applies. Keep the 3 to 5 minute spec and do not split until this is resolved. **Decided 2026-10-04:** the user is getting a 1920 x 1080 export of the 3-minute clip. When it arrives, confirm the grid matches with `tools/draw_calibration.py` (frame 0 and a late frame) and check its fps.
- ~~Clip license for both files in `footage/`.~~ Resolved 2026-10-03: both are from Pexels, free to use.

## Project definition of done

- All tests pass with `pytest`.
- `uvicorn main:app` runs, and `POST /analyze` returns counts and speeds for a real clip.
- README shows the n/s/m table, calibration error, ground truth methods, and limitations.
- Demo GIF in the repo.
- ~~Speed error against ground truth.~~ Not possible with this footage (decided 2026-10-04); README states speeds are estimates checked only against the posted limit.
