# 07 — Agent Prompts

Ready-to-paste prompts for Cursor, Antigravity, opencode, and Claude Code. Copy the block, attach the named spec files, send.

---

## The five rules behind every prompt below

**1. Attach the spec, don't describe it.** Every one of these prompts names files to attach as context. Attaching `03-api-contract.md` and saying "implement exactly this" produces correct field names. Paraphrasing it produces `plateNumber` where the contract says `plate_text`, and you find out at the checkpoint merge.

**2. One deliverable per prompt.** "Build the review queue screen" works. "Build the frontend" does not — the agent will scaffold six half-screens and none will work. If a prompt would take you more than about 45 minutes to review, split it.

**3. Every prompt ends with a verification command.** The agent must state how you'll know it worked. Without this you get code that imports cleanly and does nothing.

**4. Ask for a plan first on anything risky.** For the consensus-voting algorithm and the live/cached mode logic, make the agent write the approach before the code. Two minutes of reading a plan beats forty minutes of unpicking a wrong implementation.

**5. Never let an agent run git.** No commits, no pushes, no merges, and absolutely no conflict resolution — agents routinely resolve conflicts by deleting one side. You run git yourself.

---

## Universal preamble

Prepend to **every** prompt:

```
SCOPE FENCE — read before doing anything.
Only create or modify files under `<YOUR_DIR>/`.
Do not touch any other directory or any root-level file.
If you believe a change is needed elsewhere, describe it in your response
instead of making it.

CONTRACT — the attached spec files are frozen.
Field names, types, enum values, and route paths are exactly as written.
Do not rename anything for clarity, consistency, or style.
If a spec seems wrong or impossible, stop and tell me — do not work around it.

Do not run any git commands.
```

---

# SACHIDANAND — `pipeline/`

### P-A1 · Bake-off (hour 0)

*Attach: `01-architecture.md`, `tasks/A-pipeline-sachidanand.md`*

```
Write a single script `pipeline/bakeoff.py` that benchmarks three OCR engines on
cropped Indian licence plate images.

Input: a folder of plate crops plus `ground_truth.csv` with columns
`filename,plate_text`.

Engines:
1. fast-plate-ocr, model `cct-s-v2-global-model`
2. PaddleOCR, `en` recognition
3. EasyOCR, allowlist ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789

For each engine report: plate-level exact-match accuracy (the primary metric),
character-level accuracy, and mean milliseconds per plate. Normalise all output
to uppercase alphanumeric before comparing.

Print a summary table and write `pipeline/BAKEOFF.md` with the results.

Handle a missing engine gracefully — if an import fails, skip that engine and
report it, do not crash.

Tell me the exact command to run it.
```

### P-A2 · Detection spike (hour 1)

```
Write `pipeline/spike.py`: run fast-alpr over one video file, draw plate boxes
and detected text on each frame, write an annotated MP4, and print every
detection with its confidence.

    from fast_alpr import ALPR
    alpr = ALPR(detector_model="yolo-v9-t-384-license-plate-end2end",
                ocr_model="cct-s-v2-global-model")

This is a throwaway spike. Do not build abstractions, config systems, or classes.
One file, top to bottom, readable.

Use onnxruntime-gpu if available and print which execution provider is active so
I can confirm the GPU is being used.

Tell me the exact command to run it.
```

### P-A3 · Consensus voting — plan first (hour 8)

*Attach: `02-data-contract.md`*

```
DO NOT WRITE CODE YET.

I need character-level multi-frame consensus OCR. For one tracked vehicle I have
N reads of the same plate, each with a confidence, produced by OCR on N frames.
Reads are noisy: substitutions (B/8, O/0, I/1, S/5), occasional dropped or extra
characters, varying confidence.

Write a plan covering:
- how you handle reads of differing length before voting
- how confidence weights a per-position vote
- what happens on a tie
- how you decide `consensus_method` is `character_vote` vs `single_frame`
- how you compute an aggregate `plate_confidence`
- which edge cases break your approach

Then wait for my approval before implementing.
```

Then, after you've read and approved the plan:

```
Implement that plan as `pipeline/consensus.py`, exposing:

    def consensus_plate(reads: list[dict]) -> dict

`reads` matches the `raw_reads` shape in 02-data-contract.md.
Returns `plate_text`, `plate_confidence`, `consensus_method`.

Also write `pipeline/test_consensus.py` with cases covering: clean agreement,
heavy substitution noise, mixed lengths, all-empty reads, a single read, and a
tie. Tests must pass without any video or model — pure logic.

Tell me the exact command to run the tests.
```

> The `noisy()` function in `specs/fixtures/generate_fixtures.py` generates exactly this kind of degraded read. Point the agent at it for test data.

### P-A4 · Full pipeline (hour 10)

*Attach: `02-data-contract.md`, `tasks/A-pipeline-sachidanand.md`*

```
Build `pipeline/process.py`, runnable as:

    python -m pipeline.process --cameras data/cameras.json --out data/

For each camera segment: detect plates with fast-alpr, track vehicles with
supervision ByteTrack, apply cv2.warpPerspective to flatten each plate crop
before OCR, accumulate every frame's read per track_id, resolve with
consensus.py, compute flags.

Flags exactly per 02-data-contract.md: FORMAT_MISMATCH, UNREADABLE,
LOW_CONF_ALL_FRAMES. Flagged sightings are STORED, never dropped — this is the
core requirement, do not filter them out anywhere.

Outputs:
- data/snapshot.json, exactly the schema in 02-data-contract.md
- data/crops/SGT_XXXX.jpg, sharpest frame per sighting
- data/clips/CAMXX.mp4, annotated, under 20 MB each

`video_offset_s` is the seek position of the sighting within its own camera clip.
All timestamps ISO 8601 UTC with Z. Preserve the complete raw_reads array —
never truncate it.

Validate your own output against the schema before finishing and print a summary:
cameras, sightings, unique plates, flag counts.
```

---

# KOMALI — `api/`

### P-B1 · Skeleton (hour 0)

*Attach: `03-api-contract.md`*

```
Create a FastAPI skeleton in `api/`:
- `main.py` with `GET /health` returning the JSON shape in 03-api-contract.md
- CORS allowing http://localhost:3000, the env var FRONTEND_ORIGIN, and the
  regex https://.*\.vercel\.app
- `requirements.txt`
- `Dockerfile` listening on PORT 7860 (Hugging Face Spaces requirement — it does
  not allow custom port mapping)

Nothing else. This has to be deployable within the hour.

Tell me the exact commands to run it locally and to build the Docker image.
```

### P-B2 · Models and seeding (hour 1)

*Attach: `02-data-contract.md`, `schema.sql`, `fixtures/snapshot.example.json`*

```
Create `api/models.py` with SQLModel models mirroring schema.sql exactly, and
`api/db.py` with session handling that uses DATABASE_URL when set (Postgres) and
falls back to a local SQLite file when not. Same models must work on both.

JSON columns (raw_reads, flags) store as TEXT and expose as parsed Python objects.

Create `api/seed.py`: reads a snapshot.json path and populates the database
idempotently — re-running must not duplicate rows. This script also seeds
production, so make it safe to run repeatedly.

Verify by seeding from specs/fixtures/snapshot.example.json and printing row
counts per table. Tell me the exact command.
```

### P-B3 · Read endpoints (hour 3)

*Attach: `03-api-contract.md`, `02-data-contract.md`*

```
Implement these routes exactly as specified in 03-api-contract.md:
GET /snapshot, /cameras, /sightings, /plates/search, /trajectory/{plate}

/trajectory/{plate} is the important one. For each consecutive sighting pair,
compute a leg: look up road_distance_m from camera_links, divide by elapsed
seconds, convert to km/h. Over 150 km/h sets anomaly true.

Use this exact anomaly_reason wording, substituting the real speed:
"Implied speed 210 km/h exceeds 150 km/h threshold — possible plate cloning"
A judge reads this string verbatim with nobody there to explain it.

If a camera pair has no camera_links row: road_distance_m is null, no leg is
computed, no anomaly is claimed. Never estimate a distance.

Every list field returns [] and never null. Read endpoints must not 500 on an
empty database.

Write api/test_api.py covering each route against the seeded fixtures. Tell me
the command to run it.
```

### P-B4 · Write endpoints and analytics (hour 8)

*Attach: `03-api-contract.md`*

```
Implement, exactly per 03-api-contract.md:
GET /review, POST /review/{case_id}, GET /alerts,
POST /alerts/{id}/acknowledge, GET|POST|DELETE /watchlist,
GET /analytics/summary, /analytics/travel-times, /analytics/heatmap

Three specific requirements:

1. GET /review embeds the FULL sighting object in each case, including raw_reads
   and crop_url. One request per page — the frontend must not make a second call
   per card.

2. POST /review/{case_id} with action "corrected" validates corrected_plate
   against ^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$, returning error code
   INVALID_PLATE_FORMAT on failure. On success it also updates the underlying
   sighting's plate_text so the trajectory view reflects the correction.

3. POST /watchlist immediately scans existing sightings for matches and creates
   alerts, so adding a plate visibly produces alerts.

Analytics must be precomputed at seed time and stored, not recomputed per
request — this runs on a 2 vCPU free tier.

Extend test_api.py. Tell me the command to run it.
```

---

# KARTHIK — `web/`

### P-C1 · Scaffold and tokens (hour 0)

*Attach: `04-design-system.md`*

```
Scaffold a Next.js app in `web/`: App Router, TypeScript, Tailwind, ESLint.

Implement the design tokens from 04-design-system.md as CSS custom properties in
globals.css and expose them through tailwind.config.ts as named colours. Load
Archivo Condensed, Inter, and JetBrains Mono via next/font.

Build the persistent left rail with the six routes (/, /trajectory, /analytics,
/review, /alerts, /system) as empty pages that render their title.

Follow the palette and type scale exactly — do not substitute your own colours or
fonts, and do not add a gradient anywhere.

Tell me the command to run the dev server.
```

### P-C2 · Data layer — plan first (hour 1)

*Attach: `02-data-contract.md`, `03-api-contract.md`, `01-architecture.md`*

```
DO NOT WRITE CODE YET.

This app must render every screen correctly with the API completely unreachable.
On load it reads /snapshot.json from the static bundle and renders immediately,
while probing GET /health with a 2000ms timeout. If health responds, it upgrades
to live mode and enables write actions. If not, it stays on the snapshot with
write actions visible but disabled.

Write a plan covering: where snapshot state lives, how the health probe races
against first paint, how components consume data without caring which source it
came from, and how a single set of TypeScript types serves both.

There must be no loading spinner on first paint and no error screen, ever.

Wait for my approval before implementing.
```

Then:

```
Implement that plan.

Also generate web/lib/types.ts from 02-data-contract.md — one set of types for
both snapshot and API, since the shapes are identical. If you find yourself
needing an adapter between them, stop and tell me: it means the contract has been
broken and I need to fix the producer, not you.

Copy specs/fixtures/snapshot.example.json to web/public/snapshot.json.

Add the mode indicator chip: "Live" or "Cached dataset".
```

### P-C3 · The plate chip (hour 2 — before any screen)

*Attach: `04-design-system.md`*

```
Build web/components/PlateChip.tsx — the signature element of this design. Every
plate string in the app renders through it.

A miniature Indian number plate: hard 2px black border, 3px radius, black Archivo
Condensed characters, --plate-white ground for private and --plate-amber for
commercial. Sizes sm / md / lg.

When plate_text is null, render a hatched grey ground with the word UNREAD, so an
OCR failure is as visible on screen as a success.

Build a demo page at /_dev/chips showing every size and state so I can review it.
Do not use it anywhere else yet.
```

### P-C4 · Command Centre (hour 3)

*Attach: `04-design-system.md`*

```
Build the / route per the Command Centre spec in 04-design-system.md:

- Full-bleed react-leaflet map, CartoDB Dark Matter tiles, camera markers
- Top strip: four KPI tiles from analytics.summary, numbers in Archivo Condensed
  at 40px
- Left panel: event feed, newest first, each row = PlateChip + camera name +
  relative time + confidence bar
- Bottom: horizontal timeline scrubber. Dragging it filters both map and feed by
  time window.

The scrubber is the most important interaction in the app — it makes the dataset
feel like a recording rather than a table. Spend your effort there.

Amber and red are reserved for flags and alerts only. Do not use them
decoratively anywhere.

No empty states. The page must render fully populated on first paint.
```

### P-C5 · Trajectory (hour 8)

```
Build the /trajectory route per 04-design-system.md.

Search field, monospace, uppercases as you type, autocomplete via /plates/search
in live mode and by filtering the snapshot otherwise.

Beneath it, three pre-filled example plate chips read from meta.hero_plates in
the snapshot — never hardcode plate strings. A judge must never face an empty
search box.

On search: animate the polyline drawing along the route over ~1.2s with camera
markers lighting in sequence, respecting prefers-reduced-motion by rendering it
instantly. Right panel lists one card per sighting with PlateChip, crop
thumbnail, camera, timestamp, confidence.

Between cards render the leg: "2.1 km · 36 s · 210 km/h implied". Anomalous legs
render in --danger with the API's anomaly_reason printed in full and a CLONE
SUSPECTED chip. Print the reason string verbatim — do not rewrite it.

The route must be deep-linkable: /trajectory?plate=XXX.
```

### P-C6 · Review queue (hour 10)

```
Build the /review route. This is the most important screen in the app.

A grid of cards, one per open review case. Each card shows: the crop image, the
consensus PlateChip, a flag chip coloured by severity, and — this is the part
that matters — the raw_reads array rendered as a per-frame list that visually
collapses into the consensus result.

Five noisy reads resolving into one clean plate IS the explanation of multi-frame
consensus OCR. There is no presenter and no deck; this visual does that job. Make
the collapse legible at a glance.

Three actions: Accept, Correct, Reject. Correct opens an inline monospace field
validated against ^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$.

In cached mode the actions render but are DISABLED with a tooltip: "Live backend
unavailable — showing cached review cases." Do not hide them. Hidden features
cannot be judged.
```

---

# DAKSHA — `infra/`

### P-D1 · Repo bootstrap (hour 0)

```
Create at the repository root:
- .editorconfig: 4-space Python, 2-space TS/JSON/YAML, LF, final newline,
  trim trailing whitespace
- .prettierrc: 2 spaces, single quotes, no semicolons... (match whatever
  Karthik's Next.js default produces — check first and align to it)
- ruff.toml: line length 100, target py311
- .gitignore: __pycache__/, .venv/, node_modules/, .next/, *.onnx, .env*,
  data/crops/, data/clips/ commented out with a note that Daksha commits these
- Empty directories pipeline/ api/ web/ data/ infra/ each with a .gitkeep

These formatter configs must exist before any feature code, otherwise three
different AI tools will reformat files differently and every merge will conflict.
```

### P-D2 · Keep-warm cron (hour 2)

```
Create .github/workflows/keepwarm.yml: a scheduled workflow running every 6 hours
and on workflow_dispatch, that curls the HF Space /health endpoint with a 30s
timeout and fails loudly if it does not return 200.

Read the URL from a repository variable HF_SPACE_URL.

Free Hugging Face CPU Spaces sleep after roughly 48 hours idle; this prevents it.
```

---

## When an agent goes wrong

**It renamed a field.** Don't ask it to fix it in place — it'll rename half. Say: *"You used `plateNumber`. The contract says `plate_text`. Find every occurrence in your directory and align to the contract exactly. List what you changed."*

**It wrote 800 lines when you asked for 80.** Revert and re-prompt smaller. Don't try to prune it — the structure is usually wrong too.

**It touched another directory.** `git checkout -- <that-dir>` immediately, then re-prompt with the scope fence in caps. It will do it again if you don't.

**It claims something works and it doesn't.** Ask for the verification command and run it yourself. Agents are confident about untested code.

**It's stuck in a loop on the same error.** Stop it. Read the actual error yourself and paste a narrower prompt describing the specific fix. Three failed attempts is the signal to intervene.
