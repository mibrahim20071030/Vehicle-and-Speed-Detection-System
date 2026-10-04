import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from config import DST, LINE_A, LINE_B, SRC, ZONE
from pipeline import process_video

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov"}

app = FastAPI(title="Vehicle counting and speed estimation")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(video: UploadFile = File(...)):
    """Count vehicles and estimate their speeds in an uploaded video. Uses the camera setup in config.py."""
    if Path(video.filename or "").suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File must be .mp4, .avi or .mov")

    # closed before process_video opens it: Windows cannot open a file that is still open for writing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video.file.read())
        path = tmp.name
    try:
        return process_video(path, SRC, DST, LINE_A, LINE_B, zone=ZONE)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.remove(path)
