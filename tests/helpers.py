import cv2
import numpy as np


def make_video(path, n_frames=10, w=64, h=48, fps=10):
    """Write a small test video. Frame i is solid gray with value i * 10."""
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for i in range(n_frames):
        frame = np.full((h, w, 3), i * 10, dtype=np.uint8)
        writer.write(frame)
    writer.release()
