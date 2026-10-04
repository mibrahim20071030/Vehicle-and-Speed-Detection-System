# Progress log

CLAUDE.md is the spec. This file records what has been built, what was decided, and where to resume.

## Session 1: 2026-10-03

### Environment
- Windows 11, Python 3.14.6, virtual environment in `.venv/`. Run everything with `.\.venv\Scripts\python.exe`.
- GPU: NVIDIA GeForce RTX 5060 Laptop GPU (8 GB), driver supports CUDA 13.4.
- PyTorch was first installed as the CPU-only build (`2.14.1+cpu`). It was replaced with the CUDA build `torch 2.14.1+cu130`, `torchvision 0.29.1+cu130`. Verified: `torch.cuda.is_available()` is True, and YOLO predicts on `cuda:0`.
- Other versions: ultralytics 8.4.172, opencv-python 5.0.0, numpy 2.5.3, fastapi 0.142.2.
- `requirements.txt` says to install the CUDA build of PyTorch first (`--index-url https://download.pytorch.org/whl/cu130`); otherwise pip installs the CPU-only build.
- First YOLO call takes about 6 s of GPU warm-up. After that, about 20 ms per frame for `yolo11n.pt` (blank 640x480 frame, not a benchmark).
- `yolo11n.pt` was downloaded into the repo root (git-ignored via `*.pt`).
- Model family switched to **YOLO26** (`yolo26n/s/m.pt`) on 2026-10-03 at the user's choice; CLAUDE.md updated. `yolo26n.pt` downloaded to the repo root. `iou=` still affects YOLO26 results (7 / 10 / 19 boxes at iou 0.1 / 0.5 / 0.9 on frame 0), so NMS still runs.

### Layer 1: read video and draw (DONE, tests pass, manual check done)
- `video.py`: `open_video`, `draw_overlay` as specified. Must not change.
- `tests/helpers.py`: `make_video`. `mp4v` works on this machine (recorded in CLAUDE.md).
- `tests/test_video.py`: 3 tests.
- `pytest.ini`: `pythonpath = .` so tests can import modules from the repo root, and `testpaths = tests`.
- `scripts/annotate_line.py <in.mp4> <out.mp4>`: the manual check (draws the counting line on every frame).
- Manual check done 2026-10-03: `python scripts/annotate_line.py "footage/Untitled design.mp4" footage/annotated_line.mp4` wrote 3622 frames, 1920x1080 @ 30 fps.
  - 0 s: the line runs along the row 2 dashes, from the barrier-side shoulder edge to just past the solid right edge line, as in `calibration_overlay.png`.
  - 60 s and 110 s: the road has moved up in the frame (camera drift), so the line no longer sits on the row 2 dashes and cuts across the lanes at an angle. It still spans all 5 near lanes by eye; the left end sits at or just inside the barrier-side lane edge. The 1.9 m figure from CLAUDE.md can't be confirmed by eye. Watch lane 5 in the hand count.
  - Box, label and count drawing in `draw_overlay` has not been seen on real frames yet (Layer 2 / Layer 6).

### Calibration update (from `claude_code_update.md`)
Delivered by the user: `calibration_points.json` (source of truth, point values must not be edited), `calibration_overlay.png` (reference picture), `claude_code_update.md`.

Built:
- `config.py`: loads `SRC`, `DST`, `LINE_A`, `LINE_B`, `ZONE`, `FRAME_SIZE` from the JSON. Meter values marked `# ASSUMED`.
- `calibration.py`: `build_homography` (N >= 4 points, fits meters-to-pixels with `cv2.findHomography`, then inverts) and `to_meters`. Nothing else yet.
- `counting.py`: `side_of_line` only. Nothing else yet.
- `tests/test_calibration_config.py`: 6 tests from section 5 of the update.
- `tests/test_speed.py`: only the rewritten `test_calibration_points_map_to_destination` (4-point case) so far.
- `tools/click_points.py <image>`: prints clicked pixels, Esc quits. Not run yet (needs a display).
- `tools/draw_calibration.py <video> <out.png>`: grid, 21 points, counting line, ZONE on frame 0.
- `tools/calibration_report.py`: fit quality, held-out row 3 test, edge line check.
- `.gitignore`: `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pt`, `footage/*.mp4` (the last one added by the user before the first push).

**Test status:** 10 passed (3 Layer 1 + 6 calibration config + 1 rewritten 4-point test).

### Decisions made with the user
1. `test_calibration_points_map_to_destination` was **rewritten** to a 4-point case (0 to 1 m square). With 21 points the fit is least-squares, and 0 of 21 points are within 0.001 m. The 21-point check is `test_fit_quality`.
2. `to_meters` and `side_of_line` were built early for the calibration work. Nothing else in `calibration.py` or `counting.py` until their layers.
3. Speed: keep the Layer 7 speed-error machinery. The Speed MAE column prints `n/a` without speed clips. This clip has no independent speed ground truth, and the README must say speeds are estimates. Definition of done now includes speed error against real ground truth (GPS pass, hallway test, or dataset).
4. Count clip: keep the 3 to 5 minute spec (see the blocker below).
5. New convention: `# ASSUMED` for values that rest on an unverified assumption. `# MADE-UP` only for placeholders.
6. Calibration report baseline uses the rounded-JSON numbers: pixel RMS 2.78 / max 4.98 px, meter RMS 0.164 / max 0.370 m.
7. Stabilization is listed in CLAUDE.md as optional. `video.py` is not touched.

### Calibration report result (matches the baseline)
| Quantity | Result |
|---|---|
| Pixel error RMS / max | 2.78 / 4.98 px |
| Meter error RMS / max | 0.164 / 0.370 m |
| Held-out row 3 mean (range) | 0.34 m (0.16 to 0.67) |
| Row 2 to 3 spacing, lines a / b / c | 12.17 / 12.50 / 12.77 m (true 12.19) |
| Edge line X | -4.40 / -4.39 / -4.33 m |

### Footage (`footage/`, from Pexels, free to use per the user)
- `Untitled design.mp4` (name has a space): 1920 x 1080, 30 fps, 3622 frames (120.7 s). Calibration verified on frame 0: `footage/overlay_untitled_design.png` matches `calibration_overlay.png`.
- `original_3min.mp4`: 3840 x 2160, 29.97 fps, 5552 frames. Calibration does NOT match at native resolution: `footage/overlay_original_3min.png` shows the grid in the sky. Frame 0 shows the same scene at twice the resolution.

## Session 2: 2026-10-03 (Layer 1 finished, prep for Layer 2)

### Done
- Tests: 10 passed at the start and at the end of the session.
- Layer 1 manual check run on the real clip (details under Layer 1 above). **Layer 1 is DONE.**
- `tests/data/car.jpg` = frame 0 of `footage/Untitled design.mp4` (Pexels), 1920x1080, JPEG quality 90, 231 KB. yolo26n (conf 0.3, iou 0.5, classes 2/3/5/7) finds 10 cars, confidence 0.32 to 0.56 (dusk lowers confidence; dark cars may fall below 0.3 on the real clip, check in Layer 2's visual check).
- `yolo26n.pt` downloaded. `yolo11n.pt` is still in the repo root but no longer used (safe to delete).

### Decisions made with the user
1. **Footage license:** both clips are from Pexels, free to use (user's statement). The license notes were removed from CLAUDE.md and the open item was marked resolved. The README must still name the source and license. Caveat raised: the Pexels license does not allow redistributing unaltered copies, so putting raw clips in a public repo is a grey area; linking to the Pexels page avoids it.
2. **`.gitignore`:** ~~do NOT add entries because of licensing.~~ Changed 2026-10-04 at the user's choice: `footage/*.mp4` is git-ignored. Video files stay local only and are never pushed (GitHub's 100 MB limit, and the Pexels license does not allow redistributing unaltered copies). The README links to the Pexels pages instead.
3. **Model family: YOLO26** (`yolo26n/s/m.pt`). CLAUDE.md updated in every place that named YOLO11. Checked: `iou=` still changes results, so `detect()` keeps `iou=0.5`.
4. **`car.jpg`:** cut from the clip (frame 0).
5. **Layer 2 visual check:** add `scripts/annotate_detections.py <in.mp4> <out.mp4>` (a script, same shape as `annotate_line.py`, that calls `detect` per frame and draws the boxes with `draw_overlay`). Only process the first few hundred frames. List it in CLAUDE.md's repo layout. Only Layers 2 and 3 need such scripts; from Layer 6 on `process_video(..., output_path=...)` writes the annotated video.

### Explained to the user this session (they found the number of files confusing)
- How to run the project (PowerShell, `.venv` activation, pytest, the scripts and tools).
- The difference between a file, a module (`.py` with functions, imported, e.g. `video.py`) and a script (`.py` run with `python ...`, e.g. `scripts/annotate_line.py`), and what each file/folder in the repo is for. When adding a new file, say which group it belongs to and why it exists.

## Open items / blockers
- **3-minute file:** choose (a) test a x2 scale of the calibration points on the 4K file with `draw_calibration` (and check a late frame for drift), or (b) get a 1920 x 1080 export of the 3-minute clip. Do not split into tuning (0 to 60 s) and reporting (60 to 180 s) until the grid matches. Resizing frames conflicts with the "do not resize" rule in CLAUDE.md.
- ~~Not a git repo yet.~~ Resolved 2026-10-03: the user made the GitHub repo https://github.com/mibrahim20071030/Vehicle-and-Speed-Detection-System and pushed the first commit (`11473d2` "First Layer Completed", branch `main`). The user added `footage/*.mp4` to `.gitignore`, so no video files are in the repo (only the two overlay PNGs in `footage/`). See decision 2 of Session 2. The README should link to the Pexels pages for the clips.
- Remaining CLAUDE.md open items: ByteTrack thresholds vs `conf`, resetting tracker state, hallway test object class.

## Resume here (next session: build the remaining layers)
1. Run `.\.venv\Scripts\python.exe -m pytest` and confirm 10 pass.
2. **Layer 2:** `detector.py` (`yolo26n.pt`), `tests/test_detector.py`. `tests/data/car.jpg` is ready. Add `scripts/annotate_detections.py` for the visual check (list it in CLAUDE.md's repo layout).
3. **Layer 3:** `tracker.py`, `tests/test_tracker.py`. Needs `tests/data/one_car.mp4` (about 5 s, exactly one vehicle; cut from the clip). Check `bytetrack.yaml` thresholds vs `conf=0.1`, and how to reset tracker state.
4. **Layer 4:** the rest of `counting.py`, `tests/test_counting.py`.
5. **Layer 5:** `check_calibration` in `calibration.py`, `speed.py`, the rest of `tests/test_speed.py`.
6. **Layer 6:** `pipeline.py`, `main.py`, `tests/test_api.py`, demo video/GIF.
7. **Layer 7:** `metrics.py`, `benchmark.py`, `tests/test_metrics.py`, README. Decide the 3-minute file question first.
8. ~~Before the first push: `git init`, decide how to handle large videos.~~ Done: repo on GitHub, videos git-ignored.
