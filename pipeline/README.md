# Pipeline Package

**Owner: Sachidanand | Branch: `feat/pipeline` | Scope: `pipeline/` only**

This directory contains the **offline ANPR processing pipeline** (Plane A) for the TRACE project. It runs on a local NVIDIA-enabled machine and produces all the static data assets that the API (Plane B) serves and the frontend renders.

> **If you are an agent working on `api/`, `web/`, or `data/` -- read the "Integration Points" section below. You consume this pipeline's output; you never call it directly.**

---

## Architecture Context

The TRACE system has two planes (see `spec/01-architecture.md`):

```
PLANE A (this pipeline -- offline, Sachidanand's laptop)
  Video files + cameras.json
        |
        v
  Plate detection   (fast-alpr, YOLO-v9-t, ONNX)
        |
        v
  Vehicle tracking  (supervision ByteTrack, MIT license)
        |
        v
  Per-frame OCR     (fast-alpr built-in, cct-s-v2-global-model)
        |
        v
  Multi-frame consensus voting (character-level, confidence-weighted)
        |
        v
  Flag computation  (FORMAT_MISMATCH, UNREADABLE, LOW_CONF_ALL_FRAMES)
        |
        v
  OUTPUTS:
    data/snapshot.json       <- the complete dataset
    data/crops/*.jpg         <- one plate crop per sighting (sharpest frame)
    data/clips/CAMXX.mp4     <- one annotated video per camera (<=20 MB)

PLANE B (deployed, always available)
  Neon Postgres  <---- seeded from snapshot.json
  FastAPI on HF Space
  Next.js on Vercel  <---- also ships snapshot.json + crops + clips as static assets
```

The pipeline is **batch, not live**. It processes all camera segments once and writes structured output. This mirrors how real production ANPR works: inference near the camera, structured events to a central platform.

---

## Quick Start

```bash
# 1. Install dependencies (use a virtual environment)
pip install -r pipeline/requirements.txt

# 2. Ensure input files exist:
#    - data/cameras.json   (camera definitions from Daksha)
#    - data/clips/CAM01.mp4 ... CAM08.mp4  (video segments)

# 3. Run the pipeline:
python -m pipeline.process --cameras data/cameras.json --out data/

# 4. Validate the output:
python -m pipeline.validate_snapshot data/snapshot.json

# 5. Run unit tests:
python pipeline/test_consensus.py
```

---

## What the Pipeline Produces

### `data/snapshot.json`

The single source of truth. Contains **everything** needed to render every screen in the frontend. The schema is defined in `spec/02-data-contract.md`. Top-level structure:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-25T14:00:00Z",
  "meta": {
    "source": "batch_pipeline",
    "cameras_count": 8,
    "sightings_count": 412,
    "unique_plates": 187,
    "ocr_model": "cct-s-v2-global-model",
    "ocr_benchmark_plate_acc": 0.91,
    "footage_note": "..."
  },
  "cameras": [ ... ],
  "camera_links": [ ... ],
  "sightings": [ ... ],
  "watchlist": [],
  "alerts": [],
  "review_cases": [ ... ],
  "analytics": {
    "summary": { ... },
    "per_camera": [ ... ],
    "hourly": [ ... ],
    "travel_times": [],
    "od_matrix": []
  }
}
```

### Each sighting object

```json
{
  "id": "SGT_0001",
  "plate_text": "KA05MH1234",
  "plate_confidence": 0.872,
  "camera_id": "CAM01",
  "ts": "2026-08-25T08:12:33Z",
  "track_id": 42,
  "frame_count": 15,
  "raw_reads": [
    {"frame": 101, "text": "KA05MH1234", "conf": 0.91},
    {"frame": 103, "text": "KA05MH1Z34", "conf": 0.78},
    ...
  ],
  "consensus_method": "character_vote",
  "crop_url": "/crops/SGT_0001.jpg",
  "video_offset_s": 3.37,
  "flags": [],
  "region_guess": null
}
```

Key fields for downstream consumers:
- **`raw_reads`**: Never truncated. The review queue renders this array to visually explain how consensus was reached.
- **`video_offset_s`**: Seek position in the camera clip. The evidence player depends on this.
- **`flags`**: Array from closed enum. Flagged sightings are stored, never dropped.
- **`consensus_method`**: `"character_vote"` (>=3 reads) or `"single_frame"` (<3 reads).

### `data/crops/SGT_XXXX.jpg`

One JPEG per sighting -- the sharpest frame in the track (selected by Laplacian variance, not OCR confidence).

### `data/clips/CAMXX.mp4`

One annotated video per camera. Bounding boxes and consensus plate text burned in. Resized to 720p max. Re-encoded to stay under 20 MB (Vercel deploy limit).

---

## How the Pipeline Works (Module Guide)

### `process.py` -- Main CLI Driver

The orchestrator. For each camera segment:

1. Opens the video, initializes `fast-alpr` and `supervision.ByteTrack`
2. Iterates every frame:
   - Runs `alpr.predict(frame_rgb)` -- detection + OCR in one call (no separate OCR engine)
   - Builds `supervision.Detections` with numpy arrays
   - Calls `tracker.update_with_detections(detections)` to get stable `tracker_id`s
   - Crops the plate region, stores the OCR text + confidence per frame per track
   - Keeps the sharpest crop (Laplacian variance) for each track
3. After all frames: runs `vote_consensus()` per track
4. Computes flags: `UNREADABLE`, `FORMAT_MISMATCH`, `LOW_CONF_ALL_FRAMES`
5. Generates one annotated clip per camera
6. Builds `analytics` block (summary, per_camera, hourly)
7. Generates `review_cases` for every flagged sighting
8. Writes `snapshot.json`

**Key API details** (for anyone modifying this file):
- `fast-alpr` expects **RGB** numpy arrays (use `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)`)
- `alpr.predict()` returns `ALPRResult` objects with `.detection.bounding_box` and `.ocr.text`/`.ocr.confidence`
- ByteTrack needs `sv.Detections(xyxy=np.array(...))` and returns `detections.tracker_id`
- FPS must be read **before** `cap.release()` -- otherwise returns 0.0
- Sighting IDs are global (`SGT_0001`, `SGT_0002`, ...) not per-camera

### `consensus.py` -- Multi-Frame Character-Level Voting

The headline differentiator. Algorithm:

1. Compute modal length among non-empty reads
2. Filter: keep reads within +/-1 of modal length
3. If fewer than 3 reads survive: fall back to highest-confidence single read (`single_frame`)
4. Otherwise: determine the most common length among filtered reads (`vote_len`)
5. For each character position in `vote_len`: sum confidence weights per character, pick the winner
6. Return `(consensus_text, mean_confidence, "character_vote")`

Fully tested -- see `test_consensus.py` (10 tests covering edge cases).

### `utils.py` -- I/O and Annotation Helpers

- `load_cameras_json(path)` -- loads and returns camera definitions
- `open_video_capture(path)` -- opens video with error handling
- `draw_annotations(frame, detections)` -- draws bounding boxes + track IDs
- `save_crop(img, path)` -- saves plate crop JPEG (black placeholder if None)
- `save_annotated_clip(src, dst, frame_dets, track_texts)` -- full clip annotator:
  - Draws boxes + consensus text overlay per detection
  - Resizes to 720p max (preserving aspect ratio)
  - Re-encodes with FFmpeg if output exceeds 20 MB
- `compute_perspective_crop(frame, quad)` -- `cv2.warpPerspective` on plate quad
- `write_snapshot_json(snapshot, path)` -- pretty-printed JSON output

### `bakeoff.py` -- OCR Engine Benchmark

Runs three OCR engines on ground-truth plate crops and reports plate-level exact-match accuracy:

1. `fast-plate-ocr` (cct-s-v2-global-model)
2. PaddleOCR (en recognition)
3. EasyOCR (with A-Z0-9 allowlist)

Writes results to `pipeline/BAKEOFF.md`. The winner becomes the production OCR engine.

### `validate_snapshot.py` -- Schema Validator

Validates `snapshot.json` against `spec/02-data-contract.md`:
- Required keys at every level
- ISO 8601 UTC timestamps with `Z`
- Flag enum membership
- Cross-checks (null plate_text -> UNREADABLE flag, regex fail -> FORMAT_MISMATCH)
- raw_reads completeness
- Analytics structure

Run: `python -m pipeline.validate_snapshot data/snapshot.json`

### `test_consensus.py` -- Unit Tests

10 tests for `vote_consensus()` covering: empty input, single/two reads, character voting, confidence weighting, length tolerance, and outlier filtering.

Run: `python pipeline/test_consensus.py`

---

## Integration Points (for other agents)

### For the API agent (Komali -- `api/`)

- You receive `data/snapshot.json` and seed it into Neon Postgres
- The sighting schema is in `spec/02-data-contract.md` -- the pipeline outputs exactly this shape
- `travel_times` and `od_matrix` in analytics are empty -- you compute these at query time from sightings + camera_links
- `SPEED_ANOMALY` and `FUZZY_MERGE` flags are yours to compute at query time
- Review cases are pre-generated for flagged sightings with `status: "open"`

### For the frontend agent (Karthik -- `web/`)

- `snapshot.json` ships at `web/public/snapshot.json` -- you render from it when the API is unreachable
- `raw_reads` array powers the review queue explanation view -- never truncate it
- `video_offset_s` is the seek position for the evidence player -- it's the frame number divided by FPS
- `crop_url` is relative (e.g., `/crops/SGT_0001.jpg`) -- resolve against your static asset root
- Clips are at `/clips/CAM01.mp4` etc. -- one per camera, not per sighting
- The `analytics` block has `summary`, `per_camera`, `hourly` -- use these for dashboard widgets

### For the integration agent (Daksha -- `data/`)

- You receive the entire `data/` directory from Sachidanand -- **do not run the pipeline yourself**
- Copy `data/snapshot.json` to `web/public/snapshot.json`
- Copy `data/crops/` to `web/public/crops/`
- Copy `data/clips/` to `web/public/clips/`
- Verify clips are under 20 MB each (Vercel deploy limit)
- Supply `cameras.json` with `camera_links` for road distances -- the pipeline passes these through to snapshot.json

---

## Directory Layout

```
pipeline/
  __init__.py              # Package marker
  process.py               # Main CLI driver -- orchestrates detection, tracking, OCR, consensus
  consensus.py             # Multi-frame character-level voting algorithm
  utils.py                 # I/O helpers, annotation, perspective correction, clip encoding
  bakeoff.py               # OCR engine benchmark (3 engines, exact-match accuracy)
  validate_snapshot.py     # Schema validator for snapshot.json
  test_consensus.py        # Unit tests for consensus voting (10 tests)
  requirements.txt         # Python dependencies
  README.md                # This file
```

---

## Requirements

- **Python 3.10+**
- **CUDA-enabled GPU** recommended (ONNX Runtime GPU for fast-alpr). Falls back to CPU if unavailable.
- Install: `pip install -r pipeline/requirements.txt`

Key dependencies:
| Package | Purpose |
|---------|---------|
| `fast-alpr` | Plate detection + OCR (ONNX, MIT) |
| `supervision` | ByteTrack object tracking (MIT) |
| `opencv-python` | Video I/O, image processing |
| `onnxruntime-gpu` | GPU-accelerated inference |
| `numpy` | Array operations |
| `tqdm` | Progress bars |

---

## Conventions

- All timestamps: **ISO 8601 UTC with `Z`** (`2026-08-25T14:32:07Z`). No local time anywhere.
- All plate text: **uppercase, no spaces, no hyphens** (`KA05MH1234`).
- `null` means unknown. Never use `""` or `-1` as a sentinel.
- Indian plate regex: `^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$`
- Flagged sightings are **stored, never dropped**. This is the core design principle.

---

## Gotchas and Traps

- **`raw_reads` truncated** -> review queue loses its explanatory power -> the differentiator becomes invisible
- **Timestamps in local time** -> everything downstream is wrong and won't surface until integration
- **`video_offset_s` from wrong origin** -> evidence player seeks to black
- **Clips over 20 MB** -> Vercel deploy fails
- **FPS read after cap.release()** -> returns 0.0, all offsets become infinity (fixed in current code)
- **BGR passed to fast-alpr** -> needs RGB, will silently produce garbage OCR (fixed in current code)
- **`alpr.detect()` doesn't exist** -> the method is `alpr.predict()` (fixed in current code)

