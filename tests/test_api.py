from fastapi.testclient import TestClient

from config import DST, LINE_A, LINE_B, SRC, ZONE
from helpers import make_video                # (ours)
from main import app                          # (ours)
from pipeline import process_video            # (ours)
from video import open_video                  # (ours)

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_rejects_bad_file_type():
    r = client.post("/analyze", files={"video": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_rejects_missing_file():
    r = client.post("/analyze")
    assert r.status_code == 422


def test_process_video_output_shape(tmp_path):
    path = tmp_path / "gray.mp4"
    make_video(path)
    result = process_video(path, SRC, DST, LINE_A, LINE_B, zone=ZONE)
    assert result["frames_processed"] == 10
    assert result["counts"] == {"positive": 0, "negative": 0}
    assert result["vehicles"] == []


def test_analyze_small_video(tmp_path):
    path = tmp_path / "gray.mp4"
    make_video(path)
    with open(path, "rb") as f:
        r = client.post("/analyze", files={"video": ("gray.mp4", f, "video/mp4")})
    assert r.status_code == 200
    body = r.json()
    assert "counts" in body and "vehicles" in body


def test_process_video_frame_range(tmp_path):
    path = tmp_path / "gray.mp4"
    make_video(path)
    result = process_video(path, SRC, DST, LINE_A, LINE_B, zone=ZONE, start_frame=3, end_frame=8)
    assert result["frames_processed"] == 5
    assert result["start_frame"] == 3 and result["end_frame"] == 8
    assert result["processing_fps"] is None   # 5 frames is not more than the 5 warm-up frames


def test_process_video_writes_output(tmp_path):
    path = tmp_path / "gray.mp4"
    out_path = tmp_path / "annotated.mp4"
    make_video(path)
    process_video(path, SRC, DST, LINE_A, LINE_B, zone=ZONE, output_path=out_path)
    cap, _ = open_video(out_path)
    n = 0
    while cap.read()[0]:
        n += 1
    cap.release()
    assert n == 10
