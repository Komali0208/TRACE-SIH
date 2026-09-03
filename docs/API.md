# API reference

TRACE-SIH currently has two HTTP surfaces:

1. the Next.js same-origin route handlers under `/api/*`, used by the frontend;
2. the standalone FastAPI service in `api/`, served at its root paths such as `/health` and `/snapshot`.

Both surfaces use the same domain concepts, but their response wrappers are not identical in every endpoint. Verify the target service before writing a client.

## FastAPI service

Run locally with:

```powershell
python -m uvicorn api.main:app --reload --port 8000
```

Base URL: `http://localhost:8000`.

All errors use this envelope where the endpoint returns an error:

```json
{
  "error": {
    "code": "PLATE_NOT_FOUND",
    "message": "No sightings for plate KA99XX0000."
  }
}
```

### Read endpoints

| Method | Path | Purpose | Query/path parameters |
| --- | --- | --- | --- |
| `GET` | `/health` | Liveness and schema version | — |
| `GET` | `/snapshot` | Complete live snapshot-shaped response | — |
| `GET` | `/registry/{plate}` | Mock vehicle registry lookup | `plate` path value |
| `GET` | `/cameras` | Cameras and directed road links | — |
| `GET` | `/sightings` | Paged sighting search | `from`, `to`, `camera_id`, `plate`, `flagged`, `limit` (1–500, default 100), `offset` |
| `GET` | `/plates/search` | Plate autocomplete, up to 20 matches | `q` |
| `GET` | `/trajectory/{plate}` | Chronological sightings and derived legs | `plate` path value |
| `GET` | `/review` | Review queue with embedded sightings | `status` (default `open`), `limit`, `offset` |
| `GET` | `/alerts` | Alerts with embedded sightings | `acknowledged`, `limit`, `offset` |
| `GET` | `/watchlist` | Watchlist entries | — |
| `GET` | `/analytics/summary` | Summary metrics | — |
| `GET` | `/analytics/travel-times` | Travel-time rows sorted by delay | — |
| `GET` | `/analytics/heatmap` | Camera, hourly, and O-D analytics | `bucket` (default `hour`) |

### Write endpoints

#### Review action

```http
POST /review/{case_id}
Content-Type: application/json
```

```json
{
  "action": "corrected",
  "corrected_plate": "KA05MH1234"
}
```

`action` must be `accepted`, `corrected`, or `rejected`. `corrected_plate` is required for `corrected` and must match:

```text
^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$
```

A correction updates the linked sighting's `plate_text` as well as the review case.

#### Acknowledge an alert

```http
POST /alerts/{alert_id}/acknowledge
```

The response contains the updated alert and its linked sighting when present.

#### Manage the watchlist

```http
POST /watchlist
Content-Type: application/json
```

```json
{
  "plate_text": "KA05MH1234",
  "status": "stolen",
  "reason": "Example case reference"
}
```

`status` is one of `stolen`, `blacklisted`, or `flagged`. Adding a plate scans existing sightings and creates alerts for matches.

```http
DELETE /watchlist/{plate}
```

## Next.js route handlers

The frontend-facing routes are same-origin and live under `web/anpr-command-web/src/app/api`. They query Supabase directly through `src/lib/supabase.ts`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Determines live versus cached mode |
| `GET` | `/api/snapshot` | Builds a live snapshot from Supabase |
| `GET` | `/api/cameras` | Cameras and links |
| `GET` | `/api/sightings` | Filtered, paged sightings |
| `GET` | `/api/plates/search?q=...` | Plate autocomplete |
| `GET` | `/api/trajectory/{plate}` | Trajectory and derived legs |
| `GET` | `/api/review?status=open` | Review queue |
| `POST` | `/api/review/{id}` | Accept, correct, or reject a review case |
| `GET` | `/api/alerts` | Alerts |
| `POST` | `/api/alerts/{id}/acknowledge` | Acknowledge an alert |
| `GET` | `/api/watchlist` | Watchlist |
| `POST` | `/api/watchlist` | Add or update a watchlist plate |
| `DELETE` | `/api/watchlist?plate=...` | Remove a watchlist plate |
| `GET` | `/api/registry/{plate}` | Mock registry lookup |
| `GET` | `/api/analytics/summary` | Summary metrics |
| `GET` | `/api/analytics/travel-times` | Travel-time analytics |
| `GET` | `/api/analytics/heatmap` | Heatmap analytics |

The Next.js watchlist GET response is `{ "watchlist": [...] }`, while the standalone FastAPI endpoint currently returns the array directly. The same distinction applies to a few frontend-specific wrappers, so do not interchange response parsing without checking the service.

## Data contract

The authoritative field definitions, flag enum, timestamp rules, and snapshot shape are in [`spec/02-data-contract.md`](../spec/02-data-contract.md). The frozen route contract is in [`spec/03-api-contract.md`](../spec/03-api-contract.md).
