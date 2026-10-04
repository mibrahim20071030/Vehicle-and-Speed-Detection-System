# Vehicle Counting and Speed Estimation

![demo](demo.gif)

Counts vehicles crossing a line and estimates their speed from a fixed roadside camera.
YOLO26 (Ultralytics) detects vehicles, ByteTrack follows them from frame to frame, a line-crossing test counts
them per direction, and a homography calibrated on the road's lane markings turns pixels into meters for speed.
A FastAPI endpoint takes a video and returns the counts and speeds.

## Key results

On 1 minute of real highway footage (Grand Central Parkway, New York, dusk), compared with a hand count:

- **Counting: 83 of 83 vehicles, 0.0% error**, with all three model sizes (nano, small, medium).
- **Real time on a laptop GPU:** 59 fps with nano on a 30 fps video.
- **Speed:** median 80.6 km/h against a posted limit of 80.5 km/h (50 mph). That shows the speeds are realistic,
  but there was no independent speed measurement, so speed accuracy is **not validated** (see [Speed](#speed)).

## Results

Frames 1800 to 3599 (60 to 120 s) of the clip, near carriageway only. Same clip, machine and settings
for all three models; only the model changes. Run once with the final settings.

| Model | Counts (+/-), program vs hand | + error | - error | Count error | Speed MAE | Speed bias | Speed MAPE | FPS |
|---|---|---|---|---|---|---|---|---|
| yolo26n | +83/83, -0/0 | 0.0% | n/a | 0.0% | n/a | n/a | n/a | 59.1 |
| yolo26s | +83/83, -0/0 | 0.0% | n/a | 0.0% | n/a | n/a | n/a | 55.8 |
| yolo26m | +83/83, -0/0 | 0.0% | n/a | 0.0% | n/a | n/a | n/a | 45.2 |

- Hand count for - is 0, so the count error comes from the + direction only.
- Count error = `percent_error(program +, hand +) + percent_error(program -, hand -)`, with
  `percent_error(measured, truth) = |measured - truth| / truth x 100`. Counts were compared as totals,
  not matched car by car.
- Speed columns are `n/a`: no independent speed measurement exists for this clip.
- FPS = frames processed per second (detection, tracking, counting and speed; no video writing), after a
  5-frame warm-up. Machine: NVIDIA GeForce RTX 5060 Laptop GPU, Intel Core Ultra 7 255H, Windows 11,
  Python 3.14.6, torch 2.14.1+cu130, ultralytics 8.4.172, opencv-python 5.0.0.

### Why the bigger models first counted more than nano

The first benchmark run gave nano 83, small 85 and medium 86. Nano is the smallest model, so this needed explaining.

Tracing every extra count showed the same thing each time: **one vehicle got two boxes, so two track IDs
crossed the line in the same frame.** In most cases the vehicle was a van that the model labeled both
"car" and "truck". YOLO removes duplicate boxes (non-maximum suppression) only within one class by default,
so the car box and the truck box both survived. The bigger models are confident enough to output both
labels; nano usually outputs one.

| | Before fix (counts) | Double counts in 0 to 60 s, before / after fix |
|---|---|---|
| yolo26n | 83 | 0 / 0 |
| yolo26s | 85 | 3 / 0 |
| yolo26m | 86 | 6 / 0 |

**Fix:** `agnostic_nms=True` in the tracker, so overlapping boxes are merged whatever their class.
To avoid tuning on the reported minute, the problem was confirmed and the fix tested on the tuning
minute (0 to 60 s) first, then the reported minute was re-run once. Nano's results did not change.
Note: the problem was first noticed on the reported minute.

Nano is still the best choice here: same counts, fastest.

## Definitions

- **Reference point** of a vehicle = bottom-center of its box. Used for both counting and speed.
- **Count:** a vehicle is counted once, the first time its reference point crosses the counting line (green).
- **+ / -:** on this footage, **+ = left to right** on screen, **- = right to left**. On the near carriageway all traffic moves left to right.
- **Speed:** the reference point is converted to road meters. Speed = distance between the position now and
  10 frames earlier (0.33 s), divided by the time from the **video's** frame numbers (not the computer clock), in km/h.
  Measured only inside the speed zone (the 5 near lanes over the calibrated stretch). A vehicle's speed is the mean of its readings.

## Counting ground truth

One person hand-counted the reported minute from a copy of the clip with only the counting line and a time / frame
stamp drawn on it (`scripts/annotate_line.py`), before seeing the program's numbers. Near carriageway only, per
direction, same definition as the program. Result: 83 left to right, 0 right to left. One pass.

## Speed

No independent speed measurement exists for this clip (no GPS, radar or timed pass), so **speed error could not
be measured**. Measuring it would need a known-speed test: a car driven past a calibrated camera at a GPS-logged
speed, or a dataset with measured speeds. The code for it is in place (`metrics.speed_errors`, speed clips in `benchmark.py`).

What was checked instead: the speeds are realistic. This stretch is posted at **50 mph (80.5 km/h)**.

| Model | Vehicles with a speed | Median | Mean | 10th to 90th percentile |
|---|---|---|---|---|
| yolo26n | 84 | 80.6 km/h | 81.2 km/h | 65.7 to 99.3 km/h |
| yolo26s | 84 | 81.7 km/h | 82.0 km/h | 65.6 to 99.8 km/h |
| yolo26m | 84 | 81.6 km/h | 82.4 km/h | 66.4 to 100.6 km/h |

A badly wrong scale (for example 40 or 160 km/h medians) would show up here. A 5 to 10% error would not, and
per-vehicle accuracy is not tested. Real traffic could also run above or below the limit. Single readings within
one vehicle vary about +-10 to 15 km/h (box jitter over a 0.33 s window).

## Calibration

Real distances come from the lane markings: an assumed NYSDOT broken line of 10 ft dash + 30 ft gap (12.192 m
per cycle) and 12 ft lanes. **Not independently verified.** 21 dash corners give the homography:

- pixel error 2.78 px RMS (4.98 max); position error 0.164 m RMS (0.370 max)
- held-out test (fit on two dash rows, predict the third): 0.34 m mean error

These are consistency checks under the same marking assumption, not a check of the absolute scale.
Full details, sensitivity and camera drift: [docs/calibration.md](docs/calibration.md).

## Limitations

- One clip: one camera, dusk, one road. The reported part is 1 minute.
- Settings were picked on the first minute of the same clip (same camera and conditions), then the second minute was reported.
- The camera drifts slightly (up to about 85 px); calibration and line are fixed to frame 0. No stabilization.
- Near carriageway only; far-lane vehicles are small and hidden by the median barrier.
- A car hidden behind a nearer car can lose its track before the line and be missed.
- Vehicles already past the line in the first processed frame are not counted.
- Speed is not validated, and its scale rests on an assumed marking standard.

## What I'd do next

- Measure speed error with a known-speed test (GPS-logged pass past a calibrated camera).
- Stabilize the frames against the static horizon, so calibration and line stay on the road.
- Test on more footage: other cameras, daylight, night, rain.
- Match hand-count and program crossings car by car, not just as totals.

## Footage

[Traffic at Grand Central Parkway in New York](https://www.pexels.com/video/traffic-at-grand-central-parkway-in-new-york-12451967/),
from Pexels, under the [Pexels license](https://www.pexels.com/license/). Video files are not in this repo;
download the clip and export it at 1920 x 1080, 30 fps as `footage/Untitled design.mp4`.

## How to run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130   # NVIDIA GPU; skip for CPU
pip install -r requirements.txt
```

- Tests: `pytest`
- Benchmark (n / s / m table): `python benchmark.py`
- Demo video + GIF: `python scripts/make_demo.py [start_s] [seconds]`
- Calibration report: `python tools/calibration_report.py`
- Hand-count video: `python scripts/annotate_line.py "footage/Untitled design.mp4" footage/count_60_120.mp4 60 120`
- API: `uvicorn main:app`
  - `GET /health` returns `{"status": "ok"}`
  - `POST /analyze` with a `.mp4`, `.avi` or `.mov` file in the `video` field returns counts and per-vehicle speeds:
    ```powershell
    curl.exe -F "video=@footage/clip.mp4" http://127.0.0.1:8000/analyze
    ```
    The calibration fits this camera view only. The model loads per request; one video at a time.
