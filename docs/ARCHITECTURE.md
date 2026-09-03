# TRACE-SIH architecture

This document explains how the repository is assembled today. The frozen specifications in [`spec/`](../spec) remain authoritative when this overview and an implementation differ.

## System boundaries

TRACE separates processing from serving:

```text
┌──────────────────────────────┐
│ Plane A: offline processing  │
│ pipeline/                    │
│                              │
│ video → detection → tracking │
│       → OCR → consensus      │
│       → validation + flags   │
└──────────────┬───────────────┘
               │ snapshot.json, crops, clips
               ▼
┌──────────────────────────────────────────────────────────┐
│ Plane B: serving                                           │
│                                                          │
│  Supabase/Postgres ◄── seed snapshot                      │
│         │                                                │
│         ├── Next.js route handlers ──► browser UI         │
│         │                                                │
│         └── standalone FastAPI service ──► API clients     │
│                                                          │
│  Vercel also serves snapshot.json and media as static     │
│  assets for the frontend fallback path.                   │
└──────────────────────────────────────────────────────────┘
```

### Plane A: pipeline

`pipeline/process.py` processes camera video in batch. It detects plates, tracks vehicles with stable per-camera track IDs, collects OCR reads across frames, applies character-level confidence-weighted consensus, and writes a complete snapshot. The pipeline does not run as a live web request.

The output boundary is intentionally simple:

- `snapshot.json` contains cameras, camera links, sightings, watchlist data, alerts, review cases, registry data, and analytics;
- `crops/` contains the sharpest plate crop per sighting;
- `clips/` contains annotated camera clips.

See [`pipeline/README.md`](../pipeline/README.md) for module-level details and gotchas.

### Plane B: frontend

The Next.js app in `web/anpr-command-web` owns the operator experience and same-origin `/api/*` route handlers. Those handlers query Supabase using the browser-safe Supabase URL and anon key supplied through environment variables.

The frontend checks `/api/health` with a two-second timeout. If the check succeeds, pages request live data. If it fails, pages load `/snapshot.json` from the deployed static assets. Write actions are disabled in cached mode so the interface does not imply that a review or watchlist change was persisted.

This gives the UI a deliberate failure mode:

```text
health succeeds ──► live route handlers ──► live database
health fails    ──► static snapshot      ──► read-only UI
```

### Standalone FastAPI service

The service in `api/` is a separate FastAPI implementation of the core data contract. It uses SQLModel models and can run against:

- local SQLite by default (`api/trace.db`); or
- Postgres when `DATABASE_URL` is set.

It seeds its database from a snapshot and includes read and write endpoints for review cases, alerts, and watchlist entries. Its container listens on port `7860`.

The current frontend does not call this service directly; it calls the Next.js route handlers. Keep the two API surfaces contract-compatible when changing shared data behavior.

## Data model relationships

```text
cameras ────────┐
   │            └── camera_links (road distances)
   │
   └──────────── sightings ──────┐
                         │       ├── review_cases
                         │       └── alerts
                         │
                         └── watchlist matches

vehicle_registry is a separate mock lookup keyed by plate_text.
```

Trajectories are derived at query time by ordering a plate's sightings by timestamp. Camera-link distances are then used to calculate elapsed time and implied speed. This is why a review correction can affect later trajectory results without a separate trajectory table.

## Detection and flag semantics

The closed flag set is:

| Flag | Meaning |
| --- | --- |
| `FORMAT_MISMATCH` | Consensus text fails the Indian plate format regex |
| `UNREADABLE` | OCR cannot produce a usable text result |
| `LOW_CONF_ALL_FRAMES` | Confidence remains below the sustained threshold |
| `SPEED_ANOMALY` | A derived camera-to-camera speed exceeds 150 km/h |
| `FUZZY_MERGE` | A non-exact read was merged using edit-distance logic |

Flagged records remain in the dataset so operators can review failure cases instead of seeing only successful reads.

## Static assets and size constraints

The API returns metadata and relative media paths; it does not stream image or video bytes. Crops and clips are intended to be served as frontend static assets. Annotated clips should remain below the deployment size limit documented by the pipeline owner before being copied into the frontend's `public/` directory.

## Design principles

1. **Serve a complete read-only experience even when the API is down.**
2. **Treat the snapshot and database response shapes as one contract.**
3. **Store low-confidence and invalid reads for human review.**
4. **Compute trajectories from sightings so corrections propagate naturally.**
5. **Disclose synthetic footage and mock registry data clearly.**
