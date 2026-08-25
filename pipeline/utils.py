import json
import cv2
from pathlib import Path
import numpy as np


def load_cameras_json(path: str):
    """Load cameras.json and return list of camera dicts.
    Expected format: a JSON array where each entry has at least "id" and "clip_url".
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def open_video_capture(video_path: str):
    """Open a video file with cv2.VideoCapture.
    Raises a RuntimeError if the file cannot be opened.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video file: {video_path}")
    return cap


def draw_annotations(frame, detections, track_id=None):
    """Draw bounding boxes and optional track IDs on a frame.
    `detections` is a list of dicts with at least a ``bbox`` key: ``[x1, y1, x2, y2]``.
    Returns the annotated frame.
    """
    annotated = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = map(int, det["bbox"]) if "bbox" in det else (0, 0, 0, 0)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if "track_id" in det:
            cv2.putText(
                annotated,
                f"ID:{det['track_id']}",
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )
    return annotated


def save_crop(crop_img, out_path: Path):
    """Save a single plate crop image to ``out_path``.
    Creates parent directories if needed.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure we have a valid image; if ``crop_img`` is ``None`` write a black placeholder.
    if crop_img is None:
        crop_img = np.zeros((100, 200, 3), dtype=np.uint8)
    cv2.imwrite(str(out_path), crop_img)


def save_annotated_clip(original_video_path: str, out_path: Path, frame_detections: dict[int, list], track_texts: dict[int, str | None]):
    """Create an annotated video clip for a single track.

    * ``original_video_path`` – source video file path.
    * ``out_path`` – destination path for the annotated clip.
    * ``frame_detections`` – mapping from frame number to a list of detection dicts.
    * ``track_texts`` – mapping of ``track_id`` to consensus plate text (optional).

    The function draws bounding boxes (and track IDs) on each frame using
    :func:`draw_annotations`, optionally overlays the consensus plate text near the
    bottom centre, resizes the video to a maximum of 1280 × 720 while preserving
    aspect ratio, writes the clip with ``cv2.VideoWriter`` and re‑encodes with
    ``ffmpeg`` if the file exceeds **20 MB**.
    """
    import os
    import subprocess
    import tempfile

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Open source video
    cap = cv2.VideoCapture(original_video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video {original_video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Scaling to fit within 1280x720 while preserving aspect ratio
    max_w, max_h = 1280, 720
    scale = min(max_w / src_w, max_h / src_h, 1.0)
    out_w = int(src_w * scale)
    out_h = int(src_h * scale)

    # Temporary file for first encoding pass
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_path = Path(temp_file.name)
    temp_file.close()

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(temp_path), fourcc, fps, (out_w, out_h))
    if not writer.isOpened():
        raise RuntimeError("Failed to create VideoWriter for annotated clip")

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        # Resize if needed
        if scale < 1.0:
            frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
        detections = frame_detections.get(frame_idx, [])
        if detections:
            # Ensure each detection dict has a track_id for drawing
            # track_id is expected to be present in each detection; no injection needed
            annotated = draw_annotations(frame, detections)
        else:
            annotated = frame
        # Overlay consensus plate text per detection if available
        for det in detections:
            tid = det.get("track_id")
            plate_text = track_texts.get(tid)
            if plate_text:
                x1, y1, _, _ = map(int, det.get("bbox", [0, 0, 0, 0]))
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2
                (tw, th), _ = cv2.getTextSize(plate_text, font, font_scale, thickness)
                tx = max(x1, 0)
                ty = max(y1 - 5, th)
                cv2.putText(annotated, plate_text, (tx, ty), font, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)
        writer.write(annotated)

    writer.release()
    cap.release()

    # Helper to re‑encode with target size using ffmpeg
    def _reencode_to_target_size(src: Path, dst: Path, max_bytes: int) -> None:
        bitrate_k = 5000  # start at 5 Mbps
        while bitrate_k > 200:
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-b:v",
                f"{bitrate_k}k",
                str(dst),
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if dst.stat().st_size <= max_bytes:
                return
            bitrate_k = int(bitrate_k * 0.8)
        # Final attempt at lowest bitrate
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-b:v",
            f"{bitrate_k}k",
            str(dst),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    max_size = 20 * 1024 * 1024  # 20 MB
    if temp_path.stat().st_size > max_size:
        _reencode_to_target_size(temp_path, out_path, max_size)
        temp_path.unlink(missing_ok=True)
    else:
        temp_path.replace(out_path)



def compute_perspective_crop(frame, quad):
    """Warp the plate quadrilateral to a front‑facing rectangle.
    ``quad`` should be a list of four ``[x, y]`` points in order.
    Returns the warped plate image.
    """
    # Destination size – a reasonable fixed size for plates.
    width, height = 200, 64
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    src = np.array(quad, dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(frame, M, (width, height))
    return warped


def write_snapshot_json(snapshot: dict, out_path: Path):
    """Write the final ``snapshot.json`` with pretty formatting.
    The JSON is validated elsewhere against the schema.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
