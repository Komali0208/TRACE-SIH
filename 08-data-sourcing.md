# 08 — Data Sourcing

**Owner: Daksha. Deadline: before the build clock starts, not during it.**

This is the one task that cannot be parallelised, cannot be given to an agent, and blocks Sachidanand completely. It was originally scheduled at H3–8 in `06-timeline.md`. That was wrong. It moves to a pre-build block.

## Three separate needs

| # | Need | Volume | Solved by |
|---|---|---|---|
| 1 | Plate crops with ground-truth text | ~50 | Public datasets + 25 min of manual labelling |
| 2 | Video with legible plates | 4 locations × 3–4 min | **Filming it yourselves** |
| 3 | Same vehicle at multiple locations | 1 vehicle × 3 locations | **Staging it yourselves** |

No public dataset solves #3. Vehicle-recurring-across-a-city-network is a property of a real deployment, not of a downloadable file. This is why filming is the primary plan rather than the fallback.

## Need 1 — bake-off crops

Sources (detection boxes only — none carry text labels):

- https://www.kaggle.com/datasets/barkataliarbab/license-plate-detection-dataset-10125-images
- https://www.kaggle.com/datasets/kedarsai/indian-license-plates-with-labels
- https://universe.roboflow.com/license-plate-detection-khhkb/indian-license-plate-detection-6tmbr
- https://universe.roboflow.com/yolox-qcftu/indian-number-plate-keeo5
- https://universe.roboflow.com/indiannumberplatesdetection/indian-car-bike-number-plate (includes two-wheelers — Indian bike plates are two-row and break OCR trained on single-row plates)

Crop 50 plates, type what each one says into `ground_truth.csv` with columns `filename,plate_text`. Uppercase, no spaces. About 25 minutes of dull work, unavoidable — the accuracy figure on `/system` is only meaningful if the ground truth is real.

Include a spread: clean plates, angled plates, a few genuinely hard ones, and at least five two-wheeler plates. A bake-off run only on easy crops tells you nothing about the footage you'll actually process.

## The finding that shapes everything below

Public multi-camera traffic datasets exist and their plates are **deliberately redacted**. CityFlow / AI City Challenge covers 46 cameras across 16 intersections with 880 vehicles annotated across at least two cameras each — geometrically exactly this problem statement — but licence plates and faces were detected and blurred across every video for privacy. This is structural, not an oversight: any publishable multi-camera traffic dataset must destroy plates.

So the two needs are mutually exclusive in public data:

| Data type | Readable plates | Multi-camera |
|---|---|---|
| Plate image datasets (Kaggle, Roboflow) | Yes | No |
| Multi-camera traffic video (CityFlow, AI City) | **Redacted** | Yes |
| UFPR-ALPR | Yes, video, 30 frames/vehicle | No — and access takes 1–5 business days by email request |

Do not spend hours looking for a dataset that has both. It does not exist for privacy reasons.

## Need 2 and 3 — solved together by segmenting one long video

**The key insight: a single long dashcam drive naturally contains repeat vehicles.** You overtake a car, it overtakes you back, you both stop at the same signal. Over 20 minutes of Bengaluru traffic, dozens of vehicles appear multiple times, minutes apart.

Split that video into 8 segments, declare each segment a camera, assign coordinates along the actual route. The repeat sightings are **real** — a genuine property of the footage, not staged. That satisfies trajectory tracking honestly.

### Option A — YouTube dashcam (no filming required)

```
yt-dlp -f "bestvideo[height>=1080]" <url>
```

Search for Indian dashcam or drive-through footage, ideally 4K, ideally with the camera mounted high rather than at windshield level. Angle dominates plate legibility.

**Download ONE video and run OCR on two minutes of it before downloading any more.** If plates are illegible, the fix is a different video, not different software. Do not collect twenty clips and hope.

### Option B — 15 minutes at one window (better, and cheap)

Point a phone at a road from a balcony, hostel window, or footbridge. Record **15 minutes at maximum resolution.** One person, one quarter of an hour.

This beats every public dataset because you control the two variables that determine whether OCR works: resolution and angle. A camera above traffic sees plates flat; a camera at windshield height sees them edge-on. Split the recording into segments exactly as in Option A.

If you can do this tonight, do it. It is the single highest-return fifteen minutes available.

### Option C — still images as camera frames

Assign dataset images synthetic timestamps and camera IDs, run the pipeline over image sequences instead of video. No repeat vehicles, so trajectories come from fixtures. Honest, works, less impressive.

### Also do this today, in parallel

Request UFPR-ALPR from a university email — 4,500 annotated frames, 30 consecutive frames per vehicle, ideal for validating multi-frame consensus OCR. Turnaround is 1–5 business days, so it is a bonus if it lands, never a dependency.

## Assigning coordinates

However you get the segments, map them onto a real route. Trace the drive in Google Maps, drop 8 points along it, record lat/lon and the **road distances between consecutive points**. Measured, not straight-line — travel-time and impossible-speed analysis are meaningless otherwise.

## Privacy

You are recording real plates belonging to real people. Public street, student project, so filming is fine. But:

- Footage and derived data stay in the repo. Not published, not uploaded anywhere public
- The privacy-hashing toggle stops being a slide and becomes something you actually implemented
- State this on `/system`

A judge who notices you handled DPDP before being asked will remember it.

## Fallback chain

1. **Film it** — best data, best claim
2. **YouTube via `yt-dlp`** — download **one** clip and run OCR on it before downloading any more. If plates are illegible, stop; don't collect twenty unusable clips
3. **Still images as frames** — assign dataset images timestamps and coordinates, run the pipeline over image sequences instead of video. Less impressive, entirely honest, app looks identical
4. **Fixtures only** — `snapshot.example.json`. Every screen works, nothing is real. Acceptable floor, not the target

## `cameras.json`

Whichever path you take, produce `data/cameras.json`: each camera's id, name, real lat/lon, road name, direction, plus `camera_links` with **real road distances measured in Google Maps** — not straight-line. Travel-time and impossible-speed analysis are meaningless if these are estimated.
