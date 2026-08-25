# 03 — API Contract

**Version 1.0 — FROZEN.**

Base URL in production: the Hugging Face Space URL. Local: `http://localhost:8000`.
The frontend reads it from `NEXT_PUBLIC_API_BASE`. Never hardcode a URL in a component.

All responses are JSON. All errors use this envelope:

```json
{ "error": { "code": "PLATE_NOT_FOUND", "message": "No sightings for plate KA99XX0000." } }
```

Object shapes are exactly as defined in `02-data-contract.md`. This file specifies routes only.

---

### `GET /health`
Cheap, no DB round-trip if possible. The frontend calls this with a 2 s timeout to decide live vs cached mode.
```json
{ "status": "ok", "schema_version": "1.0", "generated_at": "2026-08-25T14:00:00Z", "mode": "live" }
```

### `GET /snapshot`
Returns the complete `snapshot.json` structure from the live database. Used by Daksha to regenerate the static fallback, and by the frontend if it wants a full live refresh.

### `GET /cameras`
`{ "cameras": [...], "camera_links": [...] }`

### `GET /sightings`
Query params: `from`, `to` (ISO), `camera_id`, `plate`, `flagged` (bool), `limit` (default 100, max 500), `offset`.
```json
{ "sightings": [...], "total": 412, "limit": 100, "offset": 0 }
```

### `GET /plates/search?q=KA05`
Autocomplete. Prefix and substring match, max 20 results.
```json
{ "matches": [ { "plate_text": "KA05MH1234", "sighting_count": 4, "cameras": ["CAM01","CAM03"] } ] }
```

### `GET /trajectory/{plate}`
The core feature. Sightings ordered by `ts`, with inter-sighting legs computed.
```json
{
  "plate_text": "KA05MH1234",
  "sightings": [ /* full sighting objects, chronological */ ],
  "legs": [
    {
      "from_sighting_id": "SGT_0012", "to_sighting_id": "SGT_0087",
      "from_camera": "CAM01", "to_camera": "CAM03",
      "road_distance_m": 2100, "elapsed_seconds": 36,
      "implied_speed_kmh": 210.0,
      "anomaly": true,
      "anomaly_reason": "Implied speed 210 km/h exceeds 150 km/h threshold — possible plate cloning"
    }
  ],
  "fuzzy_merged_from": ["KA05MHI234"],
  "watchlist_status": null
}
```
`anomaly_reason` is written by the API, not the frontend. Keep the wording — it is what a judge reads.

### `GET /analytics/summary`
Returns the `analytics.summary` object.

### `GET /analytics/travel-times`
Returns `analytics.travel_times`. Sorted by `delay_ratio` descending so the congested pairs come first.

### `GET /analytics/heatmap?bucket=hour`
`{ "per_camera": [...], "hourly": [...], "od_matrix": [...] }`

### `GET /review?status=open&limit=50`
```json
{ "cases": [ { /* review_case fields */, "sighting": { /* full sighting incl. raw_reads and crop_url */ } } ], "total": 23 }
```
The sighting **must** be embedded. The review card needs `raw_reads` and `crop_url` in one request; a second round-trip per card is not acceptable.

### `POST /review/{case_id}`
```json
{ "action": "corrected", "corrected_plate": "KA05MH1234" }
```
`action` ∈ `accepted` | `corrected` | `rejected`. `corrected_plate` required only for `corrected`, and must pass the plate regex — reject with `INVALID_PLATE_FORMAT` if not.
Returns the updated case. If a correction changes `plate_text`, the underlying sighting is updated too, so the trajectory screen reflects it immediately.

### `GET /alerts?acknowledged=false`
`{ "alerts": [ { /* alert fields */, "sighting": {...} } ] }`

### `POST /alerts/{alert_id}/acknowledge`
Returns the updated alert.

### `GET /watchlist` · `POST /watchlist` · `DELETE /watchlist/{plate}`
POST body: `{ "plate_text": "KA05MH1234", "status": "stolen", "reason": "FIR 442/2026" }`
On POST, immediately scan existing sightings for matches and generate alerts. This makes the watchlist page feel live: add a plate, alerts appear.

### `POST /infer/demo` *(stretch — build only if ahead at hour 14)*
```json
{ "clip_id": "demo_01" }
```
Runs the real pipeline on one of three pre-staged 10-second clips shipped with the API image. Synchronous, hard 60-second timeout, single-item queue. If busy: `503` with `{"error":{"code":"INFERENCE_BUSY","message":"Another clip is being processed. Try again in a moment."}}`.
**Do not accept arbitrary uploads.** An open upload endpoint on a 2 vCPU box with no one watching is a liability.

---

## Non-negotiables for the API

1. **Never serve bytes.** No images, no video, no file downloads. Crops and clips are static assets on Vercel. The API returns relative paths only.
2. **Never write to the container filesystem.** HF Spaces is ephemeral. All state goes to Neon.
3. **CORS** allows the Vercel production domain and `https://*.vercel.app`.
4. **Read-only endpoints must work on a cold empty database** by falling back to the seeded snapshot rather than returning 500.
5. Every list endpoint returns an empty array, never `null`.
