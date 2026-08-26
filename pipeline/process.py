"""Offline ANPR processing pipeline.

Usage::

    python -m pipeline.process --cameras data/cameras.json --out data/

Reads camera segments, runs detection + OCR via ``fast-alpr``, tracks with
``supervision`` ByteTrack, applies multi-frame consensus voting, and emits
``snapshot.json`` + crops + annotated clips per ``02-data-contract.md``.
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

# Fast‑ALPR – detection + OCR in one call
from fast_alpr import ALPR

# Tracking
import supervision as sv

# Local modules
from .utils import (
    load_cameras_json,
    open_video_capture,
    draw_annotations,
    save_crop,
    save_annotated_clip,
    compute_perspective_crop,
    write_snapshot_json,
)
from .consensus import vote_consensus

# Indian plate regex per spec
INDIAN_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")


def process_camera(
    camera_info: dict, out_dir: Path, alpr: ALPR, sighting_counter: int,
    base_timestamp: datetime | None = None,
):
    """Process a single camera segment.

    Args:
        camera_info: camera dict from cameras.json (must have "id" and "clip_url").
        out_dir: output directory for crops/clips.
        alpr: initialised ALPR instance.
        sighting_counter: next available global sighting counter.
        base_timestamp: UTC datetime to use as the start of this camera's
            recording.  If ``None``, defaults to ``datetime.now(UTC)``.

    Returns:
        sightings: list of sighting dicts conforming to the data contract.
        next_counter: the next available global sighting counter.
        frame_detections: mapping from frame_idx to list of normalised detection dicts.
        track_texts: mapping from track_id to consensus plate text.
    """
    cam_id = camera_info["id"]
    video_path = camera_info["clip_url"]
    cap = open_video_capture(video_path)

    # Capture FPS *before* any processing (and definitely before release)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Base timestamp for computing per-sighting ts from video offset
    if base_timestamp is None:
        base_timestamp = datetime.now(timezone.utc).replace(microsecond=0)

    tracker = sv.ByteTrack()

    # Per-track accumulator: reads, best crop, best sharpness, frame list
    tracks: dict[int, dict] = {}
    # Per-frame detection storage for annotated clip rendering
    frame_detections: dict[int, list] = {}

    frame_idx = 0
    pbar = tqdm(total=total_frames, desc=f"Processing {cam_id}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        # fast-alpr expects RGB numpy array
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        alpr_results = alpr.predict(frame_rgb)

        # Build supervision Detections from ALPR results for tracking
        if alpr_results:
            bboxes = []
            confidences = []
            ocr_data = []  # parallel list of (text, conf) tuples

            for result in alpr_results:
                # Extract bounding box — fast-alpr exposes detection bbox
                bbox = None
                if hasattr(result, "detection") and result.detection is not None:
                    det = result.detection
                    if hasattr(det, "bounding_box"):
                        bbox = list(det.bounding_box)
                    elif hasattr(det, "bbox"):
                        bbox = list(det.bbox)
                if bbox is None:
                    # Try top-level bbox
                    if hasattr(result, "bbox"):
                        bbox = list(result.bbox)
                    elif hasattr(result, "box"):
                        bbox = list(result.box)
                    else:
                        continue  # skip if we can't locate the plate

                bboxes.append(bbox)

                # Detection confidence
                det_conf = 1.0
                if hasattr(result, "detection") and result.detection is not None:
                    if hasattr(result.detection, "confidence"):
                        det_conf = float(result.detection.confidence)
                confidences.append(det_conf)

                # OCR text + confidence
                text, ocr_conf = "", 0.0
                if hasattr(result, "ocr") and result.ocr is not None:
                    text = getattr(result.ocr, "text", "") or ""
                    ocr_conf = float(getattr(result.ocr, "confidence", 0.0))
                ocr_data.append((text.strip().upper(), ocr_conf))

            if bboxes:
                detections = sv.Detections(
                    xyxy=np.array(bboxes, dtype=np.float32),
                    confidence=np.array(confidences, dtype=np.float32),
                )
                # ByteTrack assigns tracker_id
                detections = tracker.update_with_detections(detections)

                # Build normalised detection records for this frame
                frame_dets = []
                for i in range(len(detections.xyxy)):
                    tid = int(detections.tracker_id[i]) if detections.tracker_id is not None else i
                    x1, y1, x2, y2 = detections.xyxy[i]
                    text, ocr_conf = ocr_data[i] if i < len(ocr_data) else ("", 0.0)

                    det_record = {
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "track_id": tid,
                    }
                    frame_dets.append(det_record)

                    # Perspective correction on the plate crop
                    ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
                    plate_img = frame[iy1:iy2, ix1:ix2]

                    # Accumulate into track
                    if tid not in tracks:
                        tracks[tid] = {
                            "reads": [],
                            "best_crop": None,
                            "best_sharpness": -1.0,
                            "frames": [],
                        }
                    tracks[tid]["reads"].append({
                        "frame": frame_idx,
                        "text": text,
                        "conf": ocr_conf,
                    })
                    tracks[tid]["frames"].append(frame_idx)

                    # Keep sharpest crop (Laplacian variance) — spec says "sharpest frame"
                    if plate_img is not None and plate_img.size > 0:
                        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY) if len(plate_img.shape) == 3 else plate_img
                        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                        if sharpness > tracks[tid]["best_sharpness"]:
                            tracks[tid]["best_sharpness"] = sharpness
                            tracks[tid]["best_crop"] = plate_img.copy()

                frame_detections[frame_idx] = frame_dets
            else:
                frame_detections[frame_idx] = []
        else:
            frame_detections[frame_idx] = []

        pbar.update(1)

    pbar.close()
    cap.release()

    # ----- Consensus voting + sighting assembly -----
    sightings = []
    track_texts: dict[int, str | None] = {}

    for track_id, data in tracks.items():
        reads = data["reads"]
        consensus_text, consensus_conf, method = vote_consensus(reads)

        # Compute flags per spec
        flags = []
        if not consensus_text:
            flags.append("UNREADABLE")
        elif not INDIAN_PLATE_RE.match(consensus_text):
            flags.append("FORMAT_MISMATCH")

        mean_conf = float(np.mean([r["conf"] for r in reads])) if reads else 0.0
        if mean_conf < 0.55:
            flags.append("LOW_CONF_ALL_FRAMES")

        # video_offset_s — seek position of first frame in the track
        first_frame = data["frames"][0] if data["frames"] else 0
        video_offset_s = round(float(first_frame) / fps, 2)

        # UTC timestamp — base_timestamp + video position of first frame
        ts_dt = base_timestamp + timedelta(seconds=video_offset_s)
        ts_utc = ts_dt.isoformat().replace("+00:00", "Z")
        # Ensure trailing Z for naive datetimes too
        if not ts_utc.endswith("Z"):
            ts_utc += "Z"

        sighting_id = f"SGT_{sighting_counter:04d}"
        sighting_counter += 1

        sighting = {
            "id": sighting_id,
            "plate_text": consensus_text or None,
            "plate_confidence": round(consensus_conf, 3),
            "camera_id": cam_id,
            "ts": ts_utc,
            "track_id": track_id,
            "frame_count": len(reads),
            "raw_reads": reads,  # never truncated — spec requirement
            "consensus_method": method,
            "crop_url": f"/crops/{sighting_id}.jpg",
            "video_offset_s": video_offset_s,
            "flags": flags,
            "region_guess": None,
        }

        # Save crop
        crop_path = out_dir / "crops" / f"{sighting_id}.jpg"
        save_crop(data["best_crop"], crop_path)

        track_texts[track_id] = consensus_text or None
        sightings.append(sighting)

    # Save one annotated clip per camera (spec: data/clips/CAMXX.mp4)
    clip_path = out_dir / "clips" / f"{cam_id}.mp4"
    save_annotated_clip(video_path, clip_path, frame_detections, track_texts)

    return sightings, sighting_counter, frame_detections, track_texts


def build_analytics(sightings: list, cameras: list) -> dict:
    """Build the analytics block for snapshot.json per data-contract."""
    if not sightings:
        return {
            "summary": {
                "total_sightings": 0,
                "unique_plates": 0,
                "mean_confidence": 0.0,
                "open_alerts": 0,
                "open_review_cases": 0,
                "time_range": {"from": None, "to": None},
            },
            "per_camera": [],
            "hourly": [],
            "travel_times": [],
            "od_matrix": [],
        }

    unique_plates = {s["plate_text"] for s in sightings if s["plate_text"]}
    confs = [s["plate_confidence"] for s in sightings]
    timestamps = sorted([s["ts"] for s in sightings])

    # Per-camera stats
    cam_groups: dict[str, list] = defaultdict(list)
    for s in sightings:
        cam_groups[s["camera_id"]].append(s)

    per_camera = []
    for cam_id, cam_sightings in cam_groups.items():
        cam_confs = [s["plate_confidence"] for s in cam_sightings]
        per_camera.append({
            "camera_id": cam_id,
            "count": len(cam_sightings),
            "mean_confidence": round(float(np.mean(cam_confs)), 3) if cam_confs else 0.0,
        })

    # Hourly histogram
    hour_counts: dict[str, int] = defaultdict(int)
    for s in sightings:
        # Truncate to hour
        ts = s["ts"][:13] + ":00:00Z"
        hour_counts[ts] += 1
    hourly = [{"hour": h, "count": c} for h, c in sorted(hour_counts.items())]

    # Count flagged sightings for review cases count
    flagged = sum(1 for s in sightings if s["flags"])

    return {
        "summary": {
            "total_sightings": len(sightings),
            "unique_plates": len(unique_plates),
            "mean_confidence": round(float(np.mean(confs)), 3) if confs else 0.0,
            "open_alerts": 0,
            "open_review_cases": flagged,
            "time_range": {"from": timestamps[0], "to": timestamps[-1]},
        },
        "per_camera": per_camera,
        "hourly": hourly,
        "travel_times": [],  # computed at query time by Komali's API
        "od_matrix": [],     # computed at query time by Komali's API
    }


def build_review_cases(sightings: list) -> list:
    """Generate review cases for every flagged sighting."""
    cases = []
    case_counter = 1
    for s in sightings:
        if not s["flags"]:
            continue
        # One review case per sighting, using first flag as primary
        cases.append({
            "id": f"RVW_{case_counter:04d}",
            "sighting_id": s["id"],
            "flag_type": s["flags"][0],
            "status": "open",
            "corrected_plate": None,
            "reviewed_at": None,
        })
        case_counter += 1
    return cases


def main():
    parser = argparse.ArgumentParser(description="Run the offline ANPR processing pipeline")
    parser.add_argument("--cameras", required=True, help="Path to cameras.json file")
    parser.add_argument("--out", required=True, help="Output directory for data/")
    args = parser.parse_args()

    cameras_data = load_cameras_json(args.cameras)

    # cameras.json may be a plain array of cameras or an object with
    # "cameras" and "camera_links" keys.  Handle both.
    if isinstance(cameras_data, dict):
        cameras = cameras_data.get("cameras", cameras_data.get("data", []))
        camera_links = cameras_data.get("camera_links", [])
    elif isinstance(cameras_data, list):
        cameras = cameras_data
        camera_links = []
    else:
        cameras = []
        camera_links = []

    out_dir = Path(args.out)
    (out_dir / "crops").mkdir(parents=True, exist_ok=True)
    (out_dir / "clips").mkdir(parents=True, exist_ok=True)

    # Initialise ALPR — detection + OCR in one call, no separate OCR engine needed
    alpr = ALPR(
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-s-v2-global-model",
    )

    all_sightings = []
    sighting_counter = 1  # global counter across all cameras

    for cam in cameras:
        sightings, sighting_counter, _, _ = process_camera(
            cam, out_dir, alpr, sighting_counter
        )
        all_sightings.extend(sightings)

    # Build analytics and review cases
    analytics = build_analytics(all_sightings, cameras)
    review_cases = build_review_cases(all_sightings)

    # Timestamp for generation
    generated_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    # Build snapshot.json per 02-data-contract.md
    snapshot = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "meta": {
            "source": "batch_pipeline",
            "cameras_count": len(cameras),
            "sightings_count": len(all_sightings),
            "unique_plates": len({s["plate_text"] for s in all_sightings if s["plate_text"]}),
            "ocr_model": "cct-s-v2-global-model",
            "ocr_benchmark_plate_acc": None,
            "footage_note": "Processed from camera video segments via offline ANPR pipeline.",
        },
        "cameras": cameras,
        "camera_links": camera_links,
        "sightings": all_sightings,
        "watchlist": [],
        "alerts": [],
        "review_cases": review_cases,
        "analytics": analytics,
    }

    write_snapshot_json(snapshot, out_dir / "snapshot.json")
    print(f"\nPipeline completed.")
    print(f"  Sightings: {len(all_sightings)}")
    print(f"  Unique plates: {snapshot['meta']['unique_plates']}")
    print(f"  Review cases: {len(review_cases)}")
    print(f"  Snapshot: {out_dir / 'snapshot.json'}")


if __name__ == "__main__":
    main()

