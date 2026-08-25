# Task B — API & Data Layer
**Owner: Komali · Branch: `feat/api` · Scope: `api/` only**

> **Agent scope fence — paste this at the top of every prompt:**
> Only create or modify files under `api/`. Do not touch `web/`, `pipeline/`, `specs/`, `data/`, or any root-level file. If you think a change is needed elsewhere, describe it instead of making it.

You are never blocked. `specs/fixtures/snapshot.example.json` is real, schema-valid data from minute zero — seed your database from it and build every endpoint against it. When Sachidanand's real `snapshot.json` arrives at Checkpoint 2, it has the identical shape and you change nothing.

Read `02-data-contract.md` and `03-api-contract.md` in full. They are frozen; implement them exactly. If something in them is wrong or impossible, say so in the group chat — don't quietly deviate.

You have opencode unlimited, which suits this work: the API is a well-specified surface with a written contract, which is exactly the situation where a long agent loop performs well. Paste `03-api-contract.md` directly into context rather than paraphrasing it.

---

## H0–1

FastAPI skeleton. `GET /health` returning static JSON. Dockerfile listening on **port 7860** (Hugging Face Spaces requires this and does not allow custom port mapping). `requirements.txt`. That's it — Daksha needs a deployable container by hour 3.

## H1–3

SQLModel models mirroring `specs/schema.sql`. Both SQLite (local, `DATABASE_URL` unset) and Postgres (Neon, via `DATABASE_URL`) must work from the same models.

`api/seed.py` — reads a `snapshot.json` and populates the database idempotently. Run it against `specs/fixtures/snapshot.example.json`. This same script seeds production, so it needs to be re-runnable without duplicating rows.

`GET /snapshot` returning the full structure from the DB.

## H3–8 · Read endpoints

`/cameras`, `/sightings`, `/plates/search`, `/trajectory/{plate}`.

`/trajectory/{plate}` is the one that matters. For each consecutive sighting pair, compute the leg: look up `road_distance_m` from `camera_links`, divide by elapsed seconds, convert to km/h. Over 150 km/h sets `anomaly: true` and `anomaly_reason`.

**Write the `anomaly_reason` string carefully — a judge reads it verbatim, with nobody there to elaborate.** Use the wording in the contract:
`"Implied speed 210 km/h exceeds 150 km/h threshold — possible plate cloning"`

If a camera pair has no `camera_links` row, `road_distance_m` is null, no leg is computed, and no anomaly is claimed. Never guess a distance.

## H8–14 · Write endpoints and analytics

`/review` — cases with the **full sighting embedded**, including `raw_reads` and `crop_url`. One request per page, not one per card. Karthik's review grid renders `raw_reads` directly.

`POST /review/{case_id}` — accept / correct / reject. On `corrected`, validate against the plate regex and return `INVALID_PLATE_FORMAT` if it fails. Then **update the underlying sighting's `plate_text`**, so the trajectory view reflects the correction immediately. That live consequence is what makes the review queue feel like a real operator tool rather than a form.

`/alerts`, `/alerts/{id}/acknowledge`, `/watchlist` GET/POST/DELETE. On watchlist POST, immediately scan existing sightings and generate alerts — add a plate, watch alerts appear.

`/analytics/summary`, `/analytics/travel-times`, `/analytics/heatmap`.

Fuzzy matching for `/plates/search`: Levenshtein distance ≤ 2 against known plates, surfaced as near-matches distinct from exact ones. Standard `B`/`8`, `O`/`0`, `I`/`1`, `S`/`5` confusions.

## Non-negotiables

1. **Never serve bytes.** No images, no video, no downloads. Relative paths only — the frontend resolves them against Vercel's static assets. This is what keeps you inside a 2 vCPU free tier.
2. **Never write to the container filesystem.** Hugging Face Spaces is ephemeral; anything written to disk vanishes on restart. All state goes to Neon.
3. **CORS** — allow the Vercel production domain and `https://*.vercel.app`. Do this in hour 1. Discovering it at 3am costs 40 minutes.
4. **Every list endpoint returns `[]`, never `null`.**
5. **Read endpoints must not 500 on an empty database.** Fall back to the seeded snapshot.

## Definition of done

Every route in `03-api-contract.md` responds correctly against real pipeline data, deployed to the Hugging Face Space, reachable from Karthik's Vercel preview with CORS working.

## Traps

- Recomputing analytics on every request — precompute at seed time and store, or you'll time out on the free tier
- Returning `null` instead of `[]` — every frontend `.map()` breaks at once
- Serving images through the API — memory blows up, container dies
- Silently changing a field name because it reads better — the contract is frozen; message the group instead
