import sys
import time
from collections import defaultdict
from pathlib import Path
import cv2
import numpy as np
import supervision as sv

def consensus_plate(reads: list[dict]) -> dict:
    """
    reads: list of {"frame": int, "text": str, "conf": float}
    Returns: {"plate_text": str, "plate_confidence": float, "consensus_method": str}
    """
    if not reads:
        return {"plate_text": "", "plate_confidence": 0.0, "consensus_method": "single_frame"}

    valid_reads = [r for r in reads if r["text"].strip()]
    if not valid_reads:
        return {"plate_text": "", "plate_confidence": 0.0, "consensus_method": "single_frame"}

    # Find modal length
    lengths = [len(r["text"]) for r in valid_reads]
    modal_len = max(set(lengths), key=lengths.count)

    # Discard reads whose length differs from modal length by more than 1
    filtered_reads = [r for r in valid_reads if abs(len(r["text"]) - modal_len) <= 1]

    # If fewer than 3 reads contribute, fallback to best single frame
    if len(filtered_reads) < 3:
        best_read = max(valid_reads, key=lambda x: x["conf"])
        return {
            "plate_text": best_read["text"],
            "plate_confidence": float(best_read["conf"]),
            "consensus_method": "single_frame"
        }

    # Vote per character position up to modal_len
    consensus_chars = []
    for i in range(modal_len):
        votes = defaultdict(float)
        for r in filtered_reads:
            if i < len(r["text"]):
                char = r["text"][i]
                votes[char] += r["conf"]
        
        if votes:
            best_char = max(votes.items(), key=lambda x: x[1])[0]
            consensus_chars.append(best_char)

    mean_conf = float(np.mean([r["conf"] for r in filtered_reads]))
    
    return {
        "plate_text": "".join(consensus_chars),
        "plate_confidence": mean_conf,
        "consensus_method": "character_vote"
    }


def main():
    try:
        from fast_alpr import ALPR
    except ImportError:
        print("ERROR: fast_alpr not installed. Please install it.")
        sys.exit(1)

    SPIKE = Path(__file__).resolve().parent
    VIDEO_PATH = SPIKE / "video" / "sample.mp4"

    if not VIDEO_PATH.exists():
        print(f"ERROR: Video file not found at {VIDEO_PATH}")
        sys.exit(1)

    print("Initializing ALPR and ByteTrack for Consensus Benchmark...")
    alpr = ALPR(
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-s-v2-global-model"
    )
    
    tracker = sv.ByteTrack()
    cap = cv2.VideoCapture(str(VIDEO_PATH))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    tracks = defaultdict(list)
    frame_idx = 0

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
                        ocr_conf = getattr(res.ocr, "confidence", 0.0)
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

    print("\n" + "="*80)
    print(f"{'Track ID':<10} | {'Frames':<8} | {'Best Single Frame':<20} | {'Consensus Result':<20} | {'Method'}")
    print("-" * 80)
    
    for track_id, reads in sorted(tracks.items()):
        if not reads:
            continue
            
        valid_reads = [r for r in reads if r["text"].strip()]
        if not valid_reads:
            best_single = ""
        else:
            best_read = max(valid_reads, key=lambda x: x["conf"])
            best_single = best_read["text"]
            
        consensus = consensus_plate(reads)
        
        print(f"{track_id:<10} | {len(reads):<8} | {best_single:<20} | {consensus['plate_text']:<20} | {consensus['consensus_method']}")

if __name__ == "__main__":
    main()
