# Update for Claude Code: scene, calibration, and plan changes

Layer 1 (read video and draw) is already built and needs **no changes**. The changes below affect Layers 4 to 7, `config.py`, and the README plan. Update `CLAUDE.md` with them first, then build Layers 2 to 7 as planned.

Files delivered with this update (put them in the repo):
- `calibration_points.json`: the calibration points, counting line, and zone (the source of truth)
- `calibration_overlay.png`: a picture of frame 0 with everything drawn on it, for checking

## 1. The scene

- Test clip: `Untitled_design.mp4`, 1920 x 1080, 30 fps, about 2 minutes (a trimmed copy of a 3 minute clip). Evening, dusk, near LaGuardia Airport.
- Elevated, oblique side view of a divided highway. A concrete median barrier separates the **near carriageway** (5 lanes; traffic appears to move left to right in the image, judging by the tail lights) from the far carriageway.
- **Count and measure speed on the near carriageway only.** Far-lane vehicles are small and partly hidden by the barrier, and they map outside the speed zone.
- The camera is **not perfectly fixed**. Measured against frame 0 (far horizon band): about -18 px shift at 10 s, -33 px at 17 s, -47 px at 90 s, -68 px at 110 s, with about 1 to 2% scale change. Stabilization is an optional later step (see section 7).
- All pixel coordinates are in **original 1920 x 1080 frame pixels**. Do not crop or resize frames before detection or tracking. Ultralytics resizes internally and returns boxes in original coordinates.
- No people visible. The clip's license has NOT been checked yet. Check it before publishing anything derived from it.

## 2. Calibration decisions (record these in CLAUDE.md and the README)

**Source of real distances:** the road's own lane markings, not a measured distance.
- NYSDOT standard broken lane line: 10 ft line + 30 ft gap. One cycle (start of a dash to the start of the next) = 40 ft = **12.192 m**. Dash length = 10 ft = **3.048 m**.
- Lane spacing assumed 12 ft = **3.6576 m** (NYSDOT standard travel lane width).
- Dashes are assumed to start at the same place along the road on every lane line (they appear collinear across lines in the image).
- **None of this is independently verified.** The road may be city-maintained, repainted, or built to a different standard. The README must say so.

**World frame (meters):**
- X across the road: 0 = lane line `a` (the nearest dashed line to the camera), then 3.6576 (`b`), 7.3152 (`c`), 10.9728 (`d`). Increases toward the barrier.
- Y along the road: 0 = the first dash row, 12.192 = second row, 24.384 = third row. Increases to the right in the image.

**Points:** 21 points = dash starts (Y = row x 12.192) and dash ends (Y = row x 12.192 + 3.048) on 4 lane lines x 3 rows. The start of line `a` row 1 is cut off by the bottom of the frame, so only its end is used. Pixel positions were refined to sub-pixel using intensity profiles along each dash on a vehicle-free median image of frames 0 to 45. They are valid for **frame 0 of `Untitled_design.mp4`** (within about 2 px).

Dash start pixels, for orientation (end = start + 3.048 m along Y):

| | line a (X=0) | line b (X=3.66) | line c (X=7.32) | line d (X=10.97) |
|---|---|---|---|---|
| row 1 (Y=0) | cut off | (763.8, 1031.4) | (583.0, 995.0) | (445.7, 962.0) |
| row 2 (Y=12.19) | (1445.5, 939.6) | (1250.0, 916.5) | (1092.6, 896.1) | (956.1, 878.8) |
| row 3 (Y=24.38) | (1679.4, 868.2) | (1518.0, 853.5) | (1379.1, 840.2) | not used |

The full list is in `calibration_points.json`.

**Counting line (pixels):** a real cross-road line at Y = 12.192 m (the row 2 dashes), from X = -4.6 m (just beyond the right edge line) to X = 15.4 m (just beyond the barrier-side lane edge):
- `LINE_A = (1735.0, 975.1)` (right end, near the edge line)
- `LINE_B = (809.8, 861.3)` (left end, near the barrier)
- With this order of A and B, a vehicle crossing **left to right** (increasing Y) lands on the **positive** side. So `counts["positive"]` = vehicles moving left to right, `counts["negative"]` = right to left. Write this in the README.

**Speed zone (meters, `ZONE = (x_min, x_max, y_min, y_max)`):** `(-4.7, 14.8, 0.0, 27.4)`. This covers the 5 near lanes over the calibrated stretch. Sample far-lane pixels map outside it.

## 3. Changes to the plan

### 3a. `config.py`
Load the numbers from `calibration_points.json` so they are not copied by hand:

```python
import json
from pathlib import Path
import numpy as np

_DATA = json.loads((Path(__file__).parent / "calibration_points.json").read_text())

SRC = np.array([p["pixel"] for p in _DATA["points"]], dtype=np.float32)    # pixels, shape (21, 2)
DST = np.array([p["meters"] for p in _DATA["points"]], dtype=np.float32)   # meters, shape (21, 2)
LINE_A = tuple(_DATA["line_a"])
LINE_B = tuple(_DATA["line_b"])
ZONE = tuple(_DATA["zone_m"])
FRAME_SIZE = tuple(_DATA["frame_size"])
```

### 3b. `calibration.build_homography(src, dst)` (replaces the 4-point version)
- `src` and `dst`: float arrays of shape `(N, 2)` with N >= 4, same order, pixels and meters. No 3 points on one line.
- Implementation: `H_m2p, _ = cv2.findHomography(dst, src, 0)`, then `H = np.linalg.inv(H_m2p)` and `H = H / H[2, 2]`. Return `H` (pixel to meter, shape (3, 3)).
- Raise `ValueError` if shapes are wrong, N < 4, or `findHomography` returns None.
- **Why this direction:** fitting meters-to-pixels minimizes the error in pixels, which is where the measurement noise is. On our data this gives a pixel RMS of 2.78 px. Fitting pixels-to-meters directly and inverting gave 4.04 px RMS.
- `to_meters`, `check_calibration`, `speed_kmh`, `update_speeds`, `update_counts` are unchanged.

### 3c. Counting and speed
- `update_counts` uses `LINE_A`, `LINE_B` in pixels (unchanged).
- `update_speeds(..., zone=ZONE)` already skips points outside the zone. No change.
- `process_video` should be called with `src=SRC, dst=DST, line_a=LINE_A, line_b=LINE_B, zone=ZONE`.

### 3d. New tools (scripts, not part of the pipeline)
- `tools/click_points.py`: opens an image, prints the `(x, y)` pixel of each click (already described earlier).
- `tools/draw_calibration.py <video> <out.png>`: reads frame 0, draws the metric grid (lines at X = -1 lane to +4 lanes, rows at Y = 0, 12.192, 24.384), the 21 calibration points, the counting line, and the ZONE polygon. Use it to confirm the numbers still match the user's clip. It should look like `calibration_overlay.png`.
- `tools/calibration_report.py`: prints the fit quality and the held-out test (section 4).

## 4. Calibration report: expected numbers (use as a cross-check)

For the H built from all 21 points, `calibration_report.py` should print values close to these (within the test tolerances below):

| Quantity | Expected |
|---|---|
| Pixel reprojection error, RMS / max | 2.78 px / 4.96 px |
| Position error in meters when converting the 21 pixels, RMS / max | 0.167 m / 0.381 m |
| Held-out test: fit with rows 1 and 2 only, predict row 3 positions (not used in the fit), mean error | about 0.35 m (range 0.17 to 0.67 m) |
| Held-out test: predicted row 2 to row 3 spacing on lines a, b, c (true value 12.19 m) | 12.16, 12.50, 12.78 m |
| Edge line check: the solid right edge line should have a constant X. Pixels (1503, 1080), (1657, 1004), (1825, 920) | X = -4.40, -4.39, -4.33 m |

The held-out test shows that error grows when extrapolating beyond the calibrated rows. This is why `ZONE` stops at Y = 27.4 m.

These checks are consistency checks. They use the same lane-marking assumption, so they do NOT verify the absolute scale.

## 5. Tests to add (`tests/test_calibration_config.py`)

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
    # check using pixels of two known dash starts: row 2 and row 3 on line b
    after = (1518.0, 853.5)      # line b, row 3 start (Y = 24.38)
    before = (763.8, 1031.4)     # line b, row 1 start (Y = 0)
    assert side_of_line(LINE_A, LINE_B, after) > 0
    assert side_of_line(LINE_A, LINE_B, before) < 0
```

Also keep the earlier tests (`build_homography` on a simple 4-point case still works: for points that fit exactly, `to_meters` should recover them within 1e-3).

## 6. README claims for this clip

- **Counting accuracy:** valid. Hand-count the near carriageway only, per direction, using the same definition as the program (bottom-center of the box crosses the line).
- **FPS for nano, small, medium:** valid.
- **Speed:** *estimates only*. The scale comes from the NYSDOT lane-marking standard (40 ft cycle), not from a measured distance, and no independent speed measurement exists for this clip. Report: calibration residuals (section 4), the held-out test, and a sanity check against the posted speed limit (read from Street View).
- **Sensitivity (computed for a vehicle at 90 km/h, 10-frame window):**
  - Lane width assumption: +-10% changes speed by about 0.1 km/h for a vehicle moving along its lane, because speed along the road depends on the dash cycle, not the lane width.
  - Random 2 px error on the calibration points: about +-0.4 km/h.
  - A wrong assumption about the dash cycle length scales every speed by the same percentage (a 3 m / 9 m metric pattern would make true speeds about 1.6% lower than reported).
  - Camera drift, if H is not updated: speeds read about 1% low at 17 s, 1 to 3% high around 60 s, and 1 to 5% high near 110 s.
- **Limits to state:** one dusk clip, near carriageway only, handheld or slightly moving camera, speed not independently validated, clip license to be confirmed.
- Split the clip into a tuning part (first 60 s) and a reporting part (the rest) for the benchmark. Say that they come from the same camera and conditions.

## 7. Optional later: stabilization

The camera drift also moves the counting line relative to the road. By about 110 s, the barrier-side lane edge appears at about X = 16.5 m in the frame-0 calibration, versus 14.6 m at frame 0 (about 1.9 m further). The line ends at X = 15.4, so lane 5 vehicles could be partly missed late in the clip, and speeds drift as described above.

If this shows up in the hand-count comparison, add `stabilize(frame, reference_frame)` in Layer 1: estimate a similarity transform from ORB features in the **far horizon band only** (y between about 560 and 700; static airport buildings and lights) and warp the frame back to the reference with `cv2.warpAffine`. In a test, this reduced the horizon residual to about 1 to 2 px. The near-road residual was noisier (about 1 to 10 px), so verify by drawing the fixed line and calibration points over a few warped frames. Test with a synthetic image shifted by a known amount.

Run the benchmark both with and without stabilization and report the difference.

## 8. Task to give Claude Code

> Read CLAUDE.md, calibration_points.json, and this file (claude_code_update.md). Layer 1 is already built and must not change. First update CLAUDE.md with sections 1 to 7 of this file (scene, calibration decisions, the new `build_homography` spec, tools, tests, README claims). Then add `config.py` as in 3a, and `tools/draw_calibration.py` and `tools/calibration_report.py` as in 3d. Then implement Layer 5's `build_homography` as in 3b and add the tests in section 5. Run the report and confirm the numbers match section 4. Show me the output of the report and the overlay image before moving on to Layers 2 to 4. Do not change the point values in calibration_points.json. If anything in this file conflicts with CLAUDE.md, tell me instead of guessing.
