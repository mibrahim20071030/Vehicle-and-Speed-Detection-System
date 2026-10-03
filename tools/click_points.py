"""Print the (x, y) pixel of each left click on an image. Esc quits.

Usage (from the repo root):
    python tools/click_points.py frame0.png
"""
import sys

import cv2


def main(path):
    img = cv2.imread(path)
    if img is None:
        raise SystemExit(f"Could not read image: {path}")

    window = "click_points (Esc to quit)"

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            print(f"({x}, {y})", flush=True)
            cv2.circle(img, (x, y), 4, (0, 255, 0), -1)
            cv2.imshow(window, img)

    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, on_mouse)
    cv2.imshow(window, img)
    while cv2.waitKey(20) != 27:
        pass
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main(sys.argv[1])
