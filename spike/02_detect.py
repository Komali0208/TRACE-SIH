import os
import sys
import time
import re
from pathlib import Path
import cv2

try:
    from fast_alpr import ALPR
except ImportError:
    print("ERROR: fast_alpr not installed. Please install it.")
    sys.exit(1)

SPIKE = Path(__file__).resolve().parent
VIDEO_PATH = SPIKE / "video" / "sample.mp4"
OUT_DIR = SPIKE / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_VIDEO = OUT_DIR / "annotated.mp4"

if not VIDEO_PATH.exists():
    print(f"ERROR: Video file not found at {VIDEO_PATH}")
    print("Please provide spike/video/sample.mp4")
    sys.exit(1)

# Regex for Indian plate validation
INDIAN_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")

def main():
    print("Initializing ALPR...")
    # The ALPR class handles device placement internally, but we can check ONNX runtime
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        print(f"ONNX Execution Providers: {providers}")
    except ImportError:
        pass

    alpr = ALPR(
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-s-v2-global-model"
    )

    cap = cv2.VideoCapture(str(VIDEO_PATH))
    if not cap.isOpened():
        print(f"ERROR: Could not open video {VIDEO_PATH}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(OUT_VIDEO), fourcc, fps, (width, height))

    print(f"\nProcessing {total_frames} frames...")

    frames_with_detections = 0
    total_detections = 0
    total_confidence = 0.0
    regex_matches = 0

    frame_idx = 0
    start_time = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_idx += 1
        
        # fast-alpr expects RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = alpr.predict(rgb_frame)

        if results:
            frames_with_detections += 1
            for res in results:
                total_detections += 1
                
                # Extract text and confidence
                text = ""
                ocr_conf = 0.0
                if hasattr(res, "ocr") and res.ocr:
                    text = getattr(res.ocr, "text", "").strip().upper()
                    ocr_conf = getattr(res.ocr, "confidence", 0.0)

                total_confidence += ocr_conf

                if INDIAN_PLATE_RE.match(text):
                    regex_matches += 1

                print(f"Frame {frame_idx:04d}: {text} (conf: {ocr_conf:.2f})")

                # Extract bbox
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
                    x1, y1, x2, y2 = map(int, bbox)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"{text} {ocr_conf:.2f}"
                    cv2.putText(frame, label, (x1, max(0, y1 - 10)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        out.write(frame)
        
        if frame_idx % 50 == 0:
            print(f"  Processed {frame_idx}/{total_frames} frames...")

    cap.release()
    out.release()
    
    elapsed = time.perf_counter() - start_time

    print("\n" + "="*50)
    print("DETECTION SUMMARY")
    print("="*50)
    print(f"Total Frames:          {total_frames}")
    print(f"Frames with Detection: {frames_with_detections} ({(frames_with_detections/total_frames*100) if total_frames else 0:.1f}%)")
    print(f"Total Detections:      {total_detections}")
    
    mean_conf = (total_confidence / total_detections) if total_detections > 0 else 0.0
    print(f"Mean Confidence:       {mean_conf:.3f}")
    
    match_pct = (regex_matches / total_detections * 100) if total_detections > 0 else 0.0
    print(f"Indian Regex Matches:  {regex_matches} ({match_pct:.1f}%)")
    print(f"Processing Time:       {elapsed:.1f}s ({total_frames/elapsed:.1f} fps)")
    print(f"\nAnnotated video saved to {OUT_VIDEO}")

if __name__ == "__main__":
    main()
