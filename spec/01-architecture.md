# 01 — Architecture

**Version 1.0 — frozen.**

## The shape of the system

Two planes, deliberately decoupled.

```
PLANE A — PROCESSING (offline, on Sachidanand's NVIDIA laptop)
  video files + cameras.json
        |
        v
  plate detection (fast-alpr / open-image-models, ONNX)
        |
        v
  vehicle tracking (supervision ByteTrack) -> stable track_id
        |
        v
  perspective correction (cv2.warpPerspective on plate crop)
        |
        v
  OCR per frame (fast-plate-ocr cct-s-v2-global-model)
        |
        v
  multi-frame character-level consensus per track_id
        |
        v
  Indian plate regex validation -> flags
        |
        v
  OUTPUTS:
    data/snapshot.json      <- the complete dataset
    data/crops/*.jpg        <- one plate crop per sighting
    data/clips/*.mp4        <- annotated video per camera
        |
        v
PLANE B — PLATFORM (deployed, always available)
  Neon Postgres  <---- seeded from snapshot.json
        ^
        |
  FastAPI on Hugging Face Space (Docker, port 7860)
        ^
        | JSON only, never bytes
        |
  Next.js on Vercel  <---- ALSO ships snapshot.json + crops + clips as static assets
        |
        v
  Judge's browser
```

## Why it is split this way

Live video inference inside a free-tier web service is the reliable way to fail. Batch processing offline and serving pre-computed results is not a shortcut — it is how production ANPR actually works. Inference happens at or near the camera; structured events flow to a central platform. Our prototype does the same thing at a slower cadence. Say this plainly on the `/system` route; it is a strength, not a caveat.

## The static-first rule (non-negotiable)

**The frontend must render every screen correctly with the API completely unreachable.**

`snapshot.json` ships inside the Vercel build at `web/public/snapshot.json`. On load, the app reads it from the CDN and renders immediately. In parallel it pings `GET /health` with a 2000 ms timeout:

- **Responds in time** → switch to live mode. Enable write actions (review queue decisions, watchlist additions, live inference). Status chip reads `Live`.
- **Times out or errors** → stay on the snapshot. Disable write actions with a tooltip explaining why. Status chip reads `Cached dataset`.

There is no loading spinner on first paint, ever. There is no error screen, ever. The judge gets a complete working platform off a CDN edge regardless of what the free-tier backend is doing.

## Hosting

| Layer | Service | Notes |
|---|---|---|
| Frontend | Vercel Hobby | Free, always warm, CDN. Static assets live here. |
| API | Hugging Face Space (Docker SDK) | Free CPU tier: 2 vCPU / 16 GB RAM. **Must listen on port 7860.** Filesystem is ephemeral — never write state to disk. Sleeps only after ~48h idle. |
| Database | Neon Postgres free tier | Always available, survives restarts. Connection string in HF Space secrets. |
| Keep-warm | GitHub Actions cron, every 6 hours | Pings `/health`. Five lines of YAML. Prevents the 48h sleep. |

CORS on the API must allow the Vercel production domain **and** `*.vercel.app` preview domains. Configure this in the first hour or it will cost you 40 minutes at 3am.

## Library choices, and why

| Concern | Choice | Reason |
|---|---|---|
| Plate detection + OCR | `fast-alpr` + `fast-plate-ocr` | ONNX, permissive licence, ~13 ms/plate on CPU. `pip install`, not a fork. |
| OCR model | `cct-s-v2-global-model` | Current recommended default, v2 training set, region head. |
| Tracking | `supervision` ByteTrack (MIT) | Avoids the GPL `abewley/sort` fork. Drop-in. |
| Backend | FastAPI + SQLModel | Same models against SQLite locally and Postgres in prod. |
| Frontend | Next.js App Router + Tailwind + shadcn/ui + react-leaflet + recharts | Best-supported stack for AI coding agents. |

**Deliberately excluded from the build:** Ultralytics YOLOv8 (AGPL-3.0), `abewley/sort` (GPL-3.0), Kafka, Kubernetes, microservices, Redis, WebSockets. All of these belong on the `/system` target-architecture diagram and nowhere else.

## Hour-1 OCR bake-off (blocking gate)

Before any pipeline feature code, Sachidanand runs 50 cropped Indian plates through three OCR paths and records plate-level exact-match accuracy:

1. `fast-plate-ocr` `cct-s-v2-global-model`
2. PaddleOCR (`en` recognition)
3. EasyOCR with allowlist `A-Z0-9`

Highest exact-match wins and the decision is never revisited. If all three land below ~50%, fall back to forking `vipulcj/AUTOMATIC-LICENSE-PLATE-RECOGNITION-FOR-INDIAN-VEHICLES-` and lose an hour, not a day. Record the numbers — they go on the `/system` route as a real measured result, which is worth more than any claim.

## Simulated multi-camera network

We do not have a city ANPR network. We simulate one honestly:

- Source footage is split into N segments; each segment is declared a fixed camera with a real Bengaluru lat/lon.
- `cameras.json` also declares road distances between camera pairs, which is what makes travel-time and impossible-speed analysis meaningful.
- Target: **8–10 cameras**, several hundred distinct plates, a simulated timeline spanning ~2 hours. Eight cameras reads as a network; three reads as a class project.

This is disclosed verbatim on `/system`. Do not bury it.
