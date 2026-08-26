import sys
import time
from pathlib import Path
from collections import defaultdict
import cv2
import numpy as np
import supervision as sv

try:
    from fast_alpr import ALPR
except ImportError:
    print("ERROR: fast_alpr not installed. Please install it.")
    sys.exit(1)

SPIKE = Path(__file__).resolve().parent
VIDEO_PATH = SPIKE / "video" / "sample.mp4"

if not VIDEO_PATH.exists():
    print(f"ERROR: Video file not found at {VIDEO_PATH}")
    print("Please provide spike/video/sample.mp4")
    sys.exit(1)


def main():
    print("Initializing ALPR and ByteTrack...")
    alpr = ALPR(
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-s-v2-global-model"
    )
    
    tracker = sv.ByteTrack()
    cap = cv2.VideoCapture(str(VIDEO_PATH))
    
    if not cap.isOpened():
        print(f"ERROR: Could not open video {VIDEO_PATH}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Processing {total_frames} frames for tracking analysis...")

    # track_id -> list of read dicts: {"frame": int, "text": str, "conf": float, "crop": np.ndarray}
    tracks = defaultdict(list)

    frame_idx = 0
    start_time = time.perf_counter()

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
            ocr_data = []  # To keep parallel with bboxes

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
                    
                    # Detection confidence
                    det_conf = 1.0
                    if hasattr(res, "detection") and res.detection and hasattr(res.detection, "confidence"):
                        det_conf = float(res.detection.confidence)
                    confidences.append(det_conf)

                    # OCR text
                    text = ""
                    ocr_conf = 0.0
                    if hasattr(res, "ocr") and res.ocr:
                        text = getattr(res.ocr, "text", "").strip().upper()
                        ocr_conf = getattr(res.ocr, "confidence", 0.0)
                    ocr_data.append((text, ocr_conf))

            if bboxes:
                detections = sv.Detections(
                    xyxy=np.array(bboxes, dtype=np.float32),
                    confidence=np.array(confidences, dtype=np.float32)
                )
                
                tracked_detections = tracker.update_with_detections(detections)
                
                # Match tracker IDs to the original OCR data
                for i in range(len(tracked_detections.xyxy)):
                    track_id = int(tracked_detections.tracker_id[i]) if tracked_detections.tracker_id is not None else -1
                    if track_id == -1:
                        continue
                        
                    x1, y1, x2, y2 = tracked_detections.xyxy[i]
                    text, ocr_conf = ocr_data[i] if i < len(ocr_data) else ("", 0.0)
                    
                    # Crop plate for reference
                    ix1, iy1, ix2, iy2 = map(int, [x1, y1, x2, y2])
                    crop = frame[max(0, iy1):iy2, max(0, ix1):ix2].copy()

                    tracks[track_id].append({
                        "frame": frame_idx,
                        "text": text,
                        "conf": ocr_conf,
                        "crop": crop
                    })

        if frame_idx % 50 == 0:
            print(f"  Processed {frame_idx}/{total_frames} frames...")

    cap.release()
    elapsed = time.perf_counter() - start_time

    print("\n" + "="*50)
    print("TRACKING SUMMARY REPORT")
    print("="*50)
    print(f"Total distinct tracks: {len(tracks)}")
    
    mean_frames = np.mean([len(t) for t in tracks.values()]) if tracks else 0
    print(f"Mean frames per track: {mean_frames:.1f}")
    print(f"Processing Time:       {elapsed:.1f}s")
    
    print("\n--- Track Details ---")
    for track_id, reads in sorted(tracks.items()):
        print(f"\nTrack ID: {track_id} ({len(reads)} frames)")
        
        # Group reads to see if they differ
        read_counts = defaultdict(int)
        for r in reads:
            read_counts[r["text"]] += 1
            
        print("  Reads produced:")
        for text, count in sorted(read_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(reads) * 100
            print(f"    - '{text}': {count} times ({pct:.1f}%)")

if __name__ == "__main__":
    main()
