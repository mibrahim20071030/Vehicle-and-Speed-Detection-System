# Calibration details

How pixels are turned into road meters, and how well that works. Summary in the [README](../README.md#calibration).

## Source of real distances

The road's own lane markings, not a measured distance. Assumed NYSDOT standard broken lane line:
10 ft dash + 30 ft gap, so one cycle = 40 ft = **12.192 m** and a dash = **3.048 m**. Lane width assumed
12 ft = **3.6576 m**. Dashes are assumed to start at the same place along the road on every lane line.

**None of this is independently verified.** The road may be city-maintained, repainted, or built to a different standard.

## World frame

- X across the road: 0 = the nearest dashed lane line, then 3.6576, 7.3152, 10.9728 m. Increases toward the median barrier.
- Y along the road: 0 = the first dash row, 12.192 = second row, 24.384 = third row. Increases to the right on screen.

## Points and fit

21 points: dash starts and ends on 4 lane lines x 3 dash rows (one start is cut off by the frame edge,
one row is unused). Located to sub-pixel with intensity profiles along each dash, on a vehicle-free median
image of frames 0 to 45. Stored in `calibration_points.json`.

The homography is fitted meters-to-pixels with `cv2.findHomography` and inverted. That minimizes the error in
pixels, where the measurement noise is: 2.78 px RMS, versus 4.04 px when fitting pixels-to-meters directly.

Counting line: across the road at Y = 12.192 m (the second dash row), from just beyond the right edge line to
just beyond the barrier-side lane edge. Speed zone: X -4.7 to 14.8 m, Y 0 to 27.4 m (the 5 near lanes over the
calibrated stretch; error grows beyond the calibrated rows).

## Checks (`tools/calibration_report.py`)

| Check | Result |
|---|---|
| Pixel reprojection error, RMS / max | 2.78 px / 4.98 px |
| Position error of the 21 points in meters, RMS / max | 0.164 m / 0.370 m |
| Held-out test: fit rows 1 and 2 only, predict row 3 (not in the fit) | mean 0.34 m (0.16 to 0.67 m) |
| Held-out row 2 to row 3 spacing on lines a, b, c (true 12.19 m) | 12.17, 12.50, 12.77 m |
| Solid right edge line, should have constant X | -4.40, -4.39, -4.33 m |

These are consistency checks. They rely on the same lane-marking assumption, so they do **not** verify the absolute scale.

## Sensitivity of speed (vehicle at 90 km/h, 10-frame window)

- Lane width +-10%: about 0.1 km/h (speed along the road depends on the dash cycle, not the lane width).
- Random 2 px error on the calibration points: about +-0.4 km/h.
- A wrong dash cycle length scales every speed by the same percentage (a 3 m / 9 m metric pattern would make true speeds about 1.6% lower than reported).
- Camera drift (homography not updated): speeds read about 1% low at 17 s, 1 to 3% high around 60 s, and 1 to 5% high near 110 s.

## Camera drift

The camera is not perfectly fixed. Near the counting line the road moves by about -50 px (x) in the first 35 s,
then between about -35 and -85 px; y moves only a few px. The calibration and the counting line are fixed to
frame 0, so later in the clip the line sits slightly differently on the road. The line still spans all 5 near
lanes by eye, and the program's count matched the hand count in the reported minute (as totals). Stabilization (ORB features on the static
far horizon, similarity warp back to frame 0) was tested but not built.
