# 02 — Data Contract

**Version 1.0 — FROZEN.** Changes require a group-chat message and a version bump here.

This file is the single source of truth for every field name in the system. The pipeline writes it, the API serves it, the frontend renders it. If these three disagree, the build stops until they don't.

## Conventions

- All timestamps are **ISO 8601 UTC with `Z`**: `2026-08-25T14:32:07Z`. No local time anywhere in the data layer.
- All IDs are strings.
- Plate text is stored **uppercase, no spaces, no hyphens**: `KA05MH1234`.
- Coordinates are decimal degrees, WGS84.
- `null` means unknown. Never use `""` or `-1` as a sentinel.

## Indian plate format

Canonical pattern (post-1989 series):

```
^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$
```

Examples that must validate: `KA05MH1234`, `MH12AB1234`, `DL8CAF5031`, `TN09K7777`.
Anything failing this pattern gets flagged `FORMAT_MISMATCH`. It is still stored — never discarded. Storing failures instead of dropping them is the core design principle of this build.

## Flag types (closed enum)

| Flag | Meaning |
|---|---|
| `FORMAT_MISMATCH` | Consensus text does not match the Indian plate regex |
| `UNREADABLE` | Plate region detected but OCR returned empty or below threshold on every frame |
| `LOW_CONF_ALL_FRAMES` | Mean confidence < 0.55 across the whole track (sustained, not a single bad frame) |
| `SPEED_ANOMALY` | Implied speed between two sightings exceeds 150 km/h |
| `FUZZY_MERGE` | Two sightings merged across cameras by edit-distance ≤ 2, not exact match |

A sighting may carry zero, one, or several flags. `flags` is always an array, never null.

## Database schema

Authoritative DDL lives in `specs/schema.sql`. Summary:

### `cameras`
| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | `CAM01` … `CAM10` |
| `name` | TEXT | Human name, e.g. `Silk Board Junction — North` |
| `lat`, `lon` | DOUBLE | |
| `road_name` | TEXT | |
| `direction` | TEXT | `NB` / `SB` / `EB` / `WB` |
| `clip_url` | TEXT | `/clips/CAM01.mp4` — relative, resolved by the frontend |

### `camera_links`
| Column | Type | Notes |
|---|---|---|
| `from_camera` | TEXT FK | |
| `to_camera` | TEXT FK | |
| `road_distance_m` | INTEGER | Real road distance, not straight-line. Drives speed analysis. |

### `sightings`
| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | `SGT_0001` |
| `plate_text` | TEXT | Consensus result, uppercase. May be `null` if `UNREADABLE`. |
| `plate_confidence` | REAL | 0.0–1.0, mean across contributing frames |
| `camera_id` | TEXT FK | |
| `ts` | TEXT | ISO 8601 UTC |
| `track_id` | INTEGER | Unique within a camera only, not globally |
| `frame_count` | INTEGER | How many frames contributed to consensus |
| `raw_reads` | JSON array | `[{"frame": 12, "text": "KA05MH1Z34", "conf": 0.71}, …]` — this is what the review queue displays |
| `consensus_method` | TEXT | `character_vote` or `single_frame` |
| `crop_url` | TEXT | `/crops/SGT_0001.jpg` |
| `video_offset_s` | REAL | Seek position in the camera clip, for the evidence player |
| `flags` | JSON array | See enum above |
| `region_guess` | TEXT | Optional, from the OCR region head |

### `review_cases`
| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | `RVW_0001` |
| `sighting_id` | TEXT FK | |
| `flag_type` | TEXT | The primary flag that raised this case |
| `status` | TEXT | `open` / `accepted` / `corrected` / `rejected` |
| `corrected_plate` | TEXT | Set only when `status = corrected` |
| `reviewed_at` | TEXT | ISO 8601, null while open |

### `watchlist`
| Column | Type | Notes |
|---|---|---|
| `plate_text` | TEXT PK | |
| `status` | TEXT | `stolen` / `blacklisted` / `flagged` |
| `reason` | TEXT | Free text |
| `added_at` | TEXT | ISO 8601 |

### `alerts`
| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | `ALT_0001` |
| `sighting_id` | TEXT FK | |
| `plate_text` | TEXT | |
| `watchlist_status` | TEXT | |
| `ts` | TEXT | |
| `acknowledged` | BOOLEAN | Defaults false |

**Trajectories are not stored.** They are computed at query time by selecting all sightings for a plate ordered by `ts`. Storing them creates a consistency problem the moment a review correction lands.

## `snapshot.json` — the static fallback

Written by the pipeline to `data/snapshot.json`, copied by Daksha to `web/public/snapshot.json`. This is what the frontend renders when the API is unreachable, so **it must contain everything needed for every screen**.

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
    "footage_note": "Simulated 8-camera network from segmented public dashcam footage, Bengaluru coordinates."
  },
  "cameras": [ /* camera objects incl. clip_url */ ],
  "camera_links": [ /* link objects */ ],
  "sightings": [ /* full sighting objects */ ],
  "watchlist": [ /* watchlist objects */ ],
  "alerts": [ /* alert objects */ ],
  "review_cases": [ /* review case objects, joined with their sighting */ ],
  "analytics": {
    "summary": {
      "total_sightings": 412,
      "unique_plates": 187,
      "mean_confidence": 0.83,
      "open_alerts": 4,
      "open_review_cases": 23,
      "time_range": { "from": "…", "to": "…" }
    },
    "per_camera": [ { "camera_id": "CAM01", "count": 61, "mean_confidence": 0.85 } ],
    "hourly": [ { "hour": "2026-08-25T09:00:00Z", "count": 47 } ],
    "travel_times": [
      {
        "from_camera": "CAM01", "to_camera": "CAM02",
        "road_distance_m": 1450,
        "sample_count": 18,
        "median_seconds": 190,
        "current_seconds": 340,
        "delay_ratio": 1.79,
        "congested": true
      }
    ],
    "od_matrix": [ { "from_camera": "CAM01", "to_camera": "CAM04", "count": 12 } ]
  }
}
```

`snapshot.json` and the API return **identical object shapes**. The frontend must have exactly one set of TypeScript types, used for both sources. If the frontend needs a shape adapter, the contract has been broken and someone needs to fix the producer, not the consumer.

## Fixtures

`specs/fixtures/snapshot.example.json` is generated by `specs/fixtures/generate_fixtures.py`. It is schema-valid, entirely synthetic, and deliberately contains:

- 8 cameras with real Bengaluru coordinates
- ~200 sightings across ~90 plates
- **3 plates appearing at 3+ cameras** (guarantees the trajectory screen has content)
- **4 `FORMAT_MISMATCH` cases**, 3 `UNREADABLE`, 5 `LOW_CONF_ALL_FRAMES`
- **1 deliberate `SPEED_ANOMALY` pair** (implied 210 km/h)
- **2 `FUZZY_MERGE` cases** (`B`/`8` and `O`/`0` confusions)
- 3 watchlist hits producing alerts

This means the trajectory, review queue, anomaly and alert features have guaranteed demo content **regardless of what the real footage turns out to contain** — which retires the biggest planning risk in the project. Komali and Karthik build entirely against this file until hour 8.
