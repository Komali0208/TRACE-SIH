# 06 — Timeline & Checkpoints

24 working hours. Times are hours from kickoff.

## H-minus · Before the clock starts

Data sourcing happens **before** hour 0, not inside the build. See `08-data-sourcing.md`.

Daksha delivers, ahead of kickoff: ~50 labelled plate crops with `ground_truth.csv`, four filmed camera locations with legible plates, one staged repeat vehicle across three of them, and `data/cameras.json` with real coordinates and measured road distances.

If this slips, the build still runs on fixtures and every screen works — but the demo shows synthetic data instead of real detections.

## H0–1 · Foundation

| Who | Task |
|---|---|
| Daksha | Repo skeleton, formatter configs, specs committed, everyone cloned and building |
| Sachidanand | **OCR bake-off** — 50 Indian plate crops through fast-plate-ocr / PaddleOCR / EasyOCR, record plate-level accuracy |
| Komali | FastAPI skeleton, `/health` returning static JSON, Dockerfile on port 7860 |
| Karthik | `create-next-app`, Tailwind, fonts, tokens from `04-design-system.md`, left rail with six empty routes |

**Gate:** OCR winner declared. It is not revisited.

## H1–3 · Deploy the skeleton

Everything below must be live and reachable from a phone before feature work continues.

| Who | Task |
|---|---|
| Daksha | Neon project created, HF Space live serving `/health`, Vercel connected to `main`, CORS verified end to end, GH Actions keep-warm cron |
| Sachidanand | `fast-alpr` running on one video, boxes drawn, any text out |
| Komali | SQLModel models from `02-data-contract.md`, snapshot seeding script |
| Karthik | `snapshot.json` fetch from `/public`, TypeScript types, plate chip component |

**Gate — H3:** a public Vercel URL renders the left rail and reads the fixture snapshot. If this is not true at hour 3, stop feature work and fix it.

## H3–8 · Core

| Who | Task |
|---|---|
| Daksha | Segment filmed footage into camera views, finalise `cameras.json`, first pipeline run |
| Sachidanand | ByteTrack integration, per-track frame collection, crop export |
| Komali | `/cameras`, `/sightings`, `/plates/search`, `/trajectory/{plate}` with leg computation |
| Karthik | Command Centre: map, markers, KPI tiles, event feed, timeline scrubber |

## ▣ CHECKPOINT 1 — H8

Merge all branches. **Pass criteria:**
- Deployed URL renders all six routes without error
- Command Centre shows fixture data on a map with a working scrubber
- Trajectory search returns a drawn polyline for a fixture plate
- Cached-mode fallback verified by taking the API offline

Fail any of these and the next block is spent fixing, not building.

## H8–14 · Differentiators

| Who | Task |
|---|---|
| Daksha | Run the full pipeline on real footage, regenerate `snapshot.json`, `/system` route content |
| Sachidanand | **Multi-frame character-level consensus OCR**, perspective correction, flag computation |
| Komali | `/review` with embedded sightings, `POST /review`, `/alerts`, `/watchlist`, `/analytics/*` |
| Karthik | Review queue screen, alerts screen, analytics screen, evidence video player |

## ▣ CHECKPOINT 2 — H14

**Pass criteria:**
- Real pipeline data flowing through the deployed app, not fixtures
- Review queue shows real flagged cases with `raw_reads` visible
- A review correction persists and changes the trajectory view
- Watchlist alert fires end to end

## H14–19 · Polish and stretch

Fuzzy cross-camera matching, speed anomaly rendering, travel-time heatmap, guided tour overlay, mobile pass, `/system` finished, live-inference clips **only if genuinely ahead**.

## ▣ H19 — FEATURE FREEZE

Nothing new merges. Then:

- Regenerate and commit the final `snapshot.json`
- **Verify the URL from four devices on four networks**, including mobile data, not just campus wifi
- Verify it cold: open in a private window with the API deliberately stopped
- **Record a full screen-capture walkthrough as insurance**
- Write the README and the submission text

## H19–24 · Buffer

This block exists because something will have gone wrong. If nothing has, sleep — a rested team catches the broken thing at hour 23 that a wrecked team ships.

---

## Standing rule

At every checkpoint, ask one question before anything else: **is the deployed URL working right now?** Not the localhost build. The URL. If the answer is no, that is the only task anyone has until it's yes.
