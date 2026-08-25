# Task A — Processing Pipeline
**Owner: Sachidanand · Branch: `feat/pipeline` · Scope: `pipeline/` only**

> **Agent scope fence — paste this at the top of every prompt:**
> Only create or modify files under `pipeline/`. Do not touch `web/`, `api/`, `specs/`, `data/`, or any root-level file. If you think a change is needed elsewhere, describe it instead of making it.

You own the part that makes this real. Everything else in the build is presentation of what you produce. Nobody else can compensate if this doesn't work — but equally, nobody is blocked on you, because the API and frontend build against fixtures until Checkpoint 2.

Read `01-architecture.md` and `02-data-contract.md` in full before starting.

---

## H0–1 · The bake-off (blocking gate, do this before anything else)

Daksha supplies ~50 cropped Indian plate images plus `ground_truth.csv` before the build starts — see `08-data-sourcing.md`. If they are not ready on day one, crop and label them yourself; it takes about 25 minutes and the bake-off cannot proceed without real ground truth.

The set must include a spread of clean, angled, and genuinely hard plates, plus at least five two-wheeler plates — Indian bike plates are two-row and break OCR trained on single-row plates. A bake-off run only on easy crops tells you nothing.

Run all three and record **plate-level exact-match accuracy**, not character accuracy:

1. `fast-plate-ocr` with `cct-s-v2-global-model`
2. PaddleOCR, `en` recognition
3. EasyOCR with `allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'`

Write the three numbers into `pipeline/BAKEOFF.md` and post them in the group chat. Highest wins; **the decision is never revisited.** If all three are under ~50%, abandon this path and fork `vipulcj/AUTOMATIC-LICENSE-PLATE-RECOGNITION-FOR-INDIAN-VEHICLES-` instead — you'll lose an hour, not a day.

Those numbers go on the `/system` route as a measured result. A real benchmark, honestly reported, is worth more to a judge than a bigger claim.

## H1–3 · Detection running

`fast-alpr` end to end on one video segment. Boxes drawn, some text coming out, frames iterating. Don't optimise, don't structure it well, just get pixels to text.

```python
from fast_alpr import ALPR
alpr = ALPR(detector_model="yolo-v9-t-384-license-plate-end2end",
            ocr_model="cct-s-v2-global-model")
```

You have an NVIDIA laptop — install `onnxruntime-gpu`. Use it for **volume**, not for a bigger model: process every frame rather than sampling, and process all 8 camera segments. Multi-frame consensus gets dramatically better with 30 samples per track than with 6, and consensus is the headline differentiator.

**Do not fine-tune a detector on Indian data.** Six hours, competes directly with everything that actually gets seen, and the pretrained detector is not your bottleneck — OCR is.

## H3–8 · Tracking and structure

Add `supervision` ByteTrack (MIT — do not use `abewley/sort`, it's GPL). For each `track_id` within a camera segment, accumulate every frame's plate crop and OCR read.

Build the CLI:

```
python -m pipeline.process --cameras data/cameras.json --out data/
```

`cameras.json` comes from Daksha. Outputs, exactly per `02-data-contract.md`:

- `data/snapshot.json`
- `data/crops/SGT_XXXX.jpg` — one representative crop per sighting, sharpest frame in the track
- `data/clips/CAMXX.mp4` — annotated video, boxes + consensus plate text burned in, **under 20 MB each** (720p, tune CRF; these get served from Vercel's static output)

`video_offset_s` must be the seek position of the sighting inside its camera clip. The evidence player depends on it, and getting it wrong is invisible until Karthik wires the player at hour 14.

## H8–14 · The differentiators

**Multi-frame character-level consensus OCR** — the highest-value item you own.

For each track, you have N reads of the same plate. Align them by length (discard reads whose length is more than one off the modal length), then vote per character position, weighting each vote by that read's confidence. Emit:

- `plate_text` — the voted result
- `plate_confidence` — mean confidence of contributing reads
- `raw_reads` — **every** per-frame read, preserved. The review queue renders this array as the visual explanation of consensus. Do not truncate it to save space.
- `consensus_method` — `character_vote` if ≥3 reads contributed, else `single_frame`

This is genuinely new logic, not a config flag. Prototype it in a notebook against fixture-style synthetic reads *before* wiring it into the pipeline — `specs/fixtures/generate_fixtures.py` has a `noisy()` function that produces exactly the kind of degraded reads you'll be voting over, so you can test the voting logic without running a single frame of video.

**Perspective correction** — after detection, `cv2.warpPerspective` on the plate quad to flatten viewing-angle distortion before OCR. Straightforward, real accuracy gain, ~2 hours. Note for the deck: this fixes camera angle, not a physically bent plate. Don't claim otherwise.

**Flags** — compute per `02-data-contract.md`:
- `FORMAT_MISMATCH` — consensus fails `^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$`
- `UNREADABLE` — plate detected, no frame produced usable text
- `LOW_CONF_ALL_FRAMES` — mean confidence < 0.55 across the track

Flagged sightings are **stored, never dropped.** Every fork repo you'll find silently discards these. Not dropping them is the entire thesis of the project.

`SPEED_ANOMALY` and `FUZZY_MERGE` are Komali's, computed at query time from your output. You don't need to handle them.

## Definition of done

`python -m pipeline.process` runs clean on 8 camera segments and produces a `snapshot.json` that validates against the schema, plus crops and clips. Hand the whole `data/` output to Daksha — **do not commit it yourself.** Binary artefacts committed from two branches is the one merge conflict this workflow can't structurally prevent.

## Traps

- `raw_reads` truncated to save space → review queue loses its explanatory power → the differentiator becomes invisible
- Timestamps in local time → everything downstream is wrong and it won't surface until integration
- `video_offset_s` measured from the wrong origin → evidence player seeks to black
- Clips over 20 MB → Vercel deploy fails at hour 19
- Spending hour 10 improving detection accuracy by 3% instead of shipping consensus voting
