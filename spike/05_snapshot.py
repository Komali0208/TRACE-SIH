import sys
import time
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import cv2
import numpy as np
import supervision as sv

try:
    from fast_alpr import ALPR
except ImportError:
    print("ERROR: fast_alpr not installed. Please install it.")
    sys.exit(1)

# Add spike to path so we can import 04_consensus
SPIKE = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE))

from importlib.machinery import SourceFileLoader
consensus_module = SourceFileLoader("consensus_mod", str(SPIKE / "04_consensus.py")).load_module()
consensus_plate = consensus_module.consensus_plate

INDIAN_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")

VIDEO_PATH = SPIKE / "video" / "sample.mp4"
OUT_DIR = SPIKE / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_PATH = OUT_DIR / "snapshot.json"


def main():
    if not VIDEO_PATH.exists():
        print(f"ERROR: Video file not found at {VIDEO_PATH}")
        sys.exit(1)

    print("Initializing ALPR and ByteTrack for Final Snapshot...")
    alpr = ALPR(
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-s-v2-global-model"
    )
    
    tracker = sv.ByteTrack()
    cap = cv2.VideoCapture(str(VIDEO_PATH))
    
    if not cap.isOpened():
        print(f"ERROR: Could not open video {VIDEO_PATH}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration_s = total_frames / fps
    
    # Fabricate 4 cameras covering the 4 segments of the video
    segment_duration = video_duration_s / 4.0
    
    cameras = [
        {
            "id": "CAM01",
            "name": "Silk Board Junction — North",
            "lat": 12.9172,
            "lon": 77.6228,
            "road_name": "Hosur Road",
            "direction": "NB",
            "clip_url": "/clips/CAM01.mp4"
        },
        {
            "id": "CAM02",
            "name": "Silk Board Junction — South",
            "lat": 12.9170,
            "lon": 77.6229,
            "road_name": "Hosur Road",
            "direction": "SB",
            "clip_url": "/clips/CAM02.mp4"
        },
        {
            "id": "CAM03",
            "name": "HSR Layout — West",
            "lat": 12.9121,
            "lon": 77.6379,
            "road_name": "Outer Ring Road",
            "direction": "WB",
            "clip_url": "/clips/CAM03.mp4"
        },
        {
            "id": "CAM04",
            "name": "Koramangala — East",
            "lat": 12.9345,
            "lon": 77.6266,
            "road_name": "Koramangala 80ft Road",
            "direction": "EB",
            "clip_url": "/clips/CAM04.mp4"
        }
    ]

    tracks = defaultdict(list)
    frame_idx = 0

    print(f"Processing {total_frames} frames to generate sightings...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_idx += 1
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = alpr.predict(rgb_frame)
        
        if results:
            bboxes = []
            confidences = []
            ocr_data = []

            for res in results:
                bbox = None
                if hasattr(res, "detection") and res.detection:
                    if hasattr(res.detection, "bounding_box"):
                        bbox = res.detection.bounding_box
                    elif hasattr(res.detection, "bbox"):
                        bbox = res.detection.bbox
                if not bbox and hasattr(res, "bbox"):
                    bbox = res.bbox
                elif not bbox and hasattr(res, "box"):
                    bbox = res.box

                if bbox:
                    bboxes.append(list(bbox))
                    
                    det_conf = 1.0
                    if hasattr(res, "detection") and res.detection and hasattr(res.detection, "confidence"):
                        det_conf = float(res.detection.confidence)
                    confidences.append(det_conf)

                    text = ""
                    ocr_conf = 0.0
                    if hasattr(res, "ocr") and res.ocr:
                        text = getattr(res.ocr, "text", "").strip().upper()
                        ocr_conf = float(getattr(res.ocr, "confidence", 0.0))
                    ocr_data.append((text, ocr_conf))

            if bboxes:
                detections = sv.Detections(
                    xyxy=np.array(bboxes, dtype=np.float32),
                    confidence=np.array(confidences, dtype=np.float32)
                )
                tracked_detections = tracker.update_with_detections(detections)
                
                for i in range(len(tracked_detections.xyxy)):
                    track_id = int(tracked_detections.tracker_id[i]) if tracked_detections.tracker_id is not None else -1
                    if track_id == -1:
                        continue
                    
                    text, ocr_conf = ocr_data[i] if i < len(ocr_data) else ("", 0.0)
                    tracks[track_id].append({
                        "frame": frame_idx,
                        "text": text,
                        "conf": ocr_conf,
                    })

        if frame_idx % 50 == 0:
            print(f"  Processed {frame_idx}/{total_frames} frames...")

    cap.release()

    sightings = []
    review_cases = []
    
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
    sighting_counter = 1
    review_counter = 1

    unique_plates = set()
    confs = []

    for track_id, reads in tracks.items():
        if not reads:
            continue
            
        first_frame = reads[0]["frame"]
        video_offset_s = round(first_frame / fps, 2)
        
        # Determine which "camera" segment this track falls into
        camera_idx = min(int(video_offset_s // segment_duration), 3)
        camera_id = cameras[camera_idx]["id"]
        
        consensus = consensus_plate(reads)
        plate_text = consensus["plate_text"] or None
        plate_confidence = round(consensus["plate_confidence"], 3)
        
        flags = []
        if not plate_text:
            flags.append("UNREADABLE")
        elif not INDIAN_PLATE_RE.match(plate_text):
            flags.append("FORMAT_MISMATCH")
            
        if reads and (sum(r["conf"] for r in reads) / len(reads)) < 0.55:
            flags.append("LOW_CONF_ALL_FRAMES")
            
        if plate_text:
            unique_plates.add(plate_text)
            
        confs.append(plate_confidence)
            
        sighting_id = f"SGT_{sighting_counter:04d}"
        sighting_counter += 1
        
        sighting = {
            "id": sighting_id,
            "plate_text": plate_text,
            "plate_confidence": plate_confidence,
            "camera_id": camera_id,
            "ts": generated_at, # just use generation time for spike
            "track_id": track_id,
            "frame_count": len(reads),
            "raw_reads": reads,
            "consensus_method": consensus["consensus_method"],
            "crop_url": f"/crops/{sighting_id}.jpg",
            "video_offset_s": video_offset_s,
            "flags": flags,
            "region_guess": None
        }
        
        sightings.append(sighting)
        
        if flags:
            review_cases.append({
                "id": f"RVW_{review_counter:04d}",
                "sighting_id": sighting_id,
                "flag_type": flags[0],
                "status": "open",
                "corrected_plate": None,
                "reviewed_at": None,
                "sighting": sighting # join for snapshot.json as per schema
            })
            review_counter += 1

    mean_conf = float(np.mean(confs)) if confs else 0.0

    snapshot = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "meta": {
            "source": "spike_pipeline",
            "cameras_count": len(cameras),
            "sightings_count": len(sightings),
            "unique_plates": len(unique_plates),
            "ocr_model": "cct-s-v2-global-model",
            "ocr_benchmark_plate_acc": None,
            "footage_note": "Fabricated cameras from split video for spike."
        },
        "cameras": cameras,
        "camera_links": [],
        "sightings": sightings,
        "watchlist": [],
        "alerts": [],
        "review_cases": review_cases,
        "analytics": {
            "summary": {
                "total_sightings": len(sightings),
                "unique_plates": len(unique_plates),
                "mean_confidence": round(mean_conf, 3),
                "open_alerts": 0,
                "open_review_cases": len(review_cases),
                "time_range": {"from": generated_at, "to": generated_at}
            },
            "per_camera": [],
            "hourly": [],
            "travel_times": [],
            "od_matrix": []
        }
    }

    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"\nSnapshot written to {SNAPSHOT_PATH}")
    print(f"Generated {len(sightings)} sightings across 4 virtual cameras.")

if __name__ == "__main__":
    main()
