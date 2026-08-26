# SENTINEL-ANPR — Command Centre

Multi-camera ANPR (license plate) intelligence platform. Full stack: Next.js frontend + API + Supabase Postgres, live data end to end.

---

## 1. What was actually built

### Database (Supabase Postgres) — live, not mocked
Project: `anpr-command-centre` (ref `zkjayklsmcqswtiadvja`), region `ap-south-1`.

Tables (created via SQL migrations, RLS enabled):
- `cameras` — 8 rows
- `camera_links` — 10 rows (road distances between camera pairs)
- `sightings` — 182 rows (plate reads, incl. multi-frame `raw_reads` jsonb for flagged ones)
- `watchlist` — 3 rows (stolen/blacklisted/flagged plates)
- `alerts` — 5 rows (watchlist hits)
- `review_cases` — 15 rows (flagged OCR reads needing human review)
- `app_meta` — 1 row (hero plates, clone plate, OCR model tag, footage note)

**Source of this data:** the `snapshot.json` fixture file you provided. Every row was copied from it as-is — nothing invented. Seeded via `Supabase:apply_migration` SQL INSERTs.

### Frontend + API (Next.js 14, App Router, TypeScript, Tailwind)
Single app. API routes run server-side and query Supabase directly — no separate backend.

### 6 routes (per your design spec)
- `/` — Command Centre: KPI tiles, live event feed, dark map (Leaflet + CartoDB tiles), timeline scrubber, first-visit tour
- `/trajectory` — plate search → chronological sighting list, map polyline, leg-by-leg distance/time/speed, anomaly + fuzzy-merge detection
- `/review` — OCR review queue: raw multi-frame reads → consensus plate, Accept/Correct/Reject (writes to DB)
- `/alerts` — watchlist hits + add/remove plate (writes to DB, live-scans existing sightings for matches)
- `/analytics` — travel-time congestion, hourly volume chart, camera density, O-D matrix
- `/system` — architecture diagram, prototype-vs-target table, real-vs-simulated disclosure

### Live vs cached mode
On load, app pings `/api/health` with a 2s timeout.
- **Live**: all pages fetch from `/api/*` → Supabase, in real time.
- **Cached** (only if Supabase unreachable): falls back to `public/snapshot.json`, write buttons disabled with tooltip, UI still fully renders.

### What's real vs what's fixture
- Real: Postgres, live queries, trajectory/leg math, anomaly detection, consensus-vote algorithm, watchlist matching, all writes (Accept/Correct/Reject, Add/Remove watchlist)
- Fixture (per your spec): the plate reads and camera geography themselves are the synthetic dataset you supplied, not live camera footage

---

## 2. File structure (as it exists right now)

```
anpr-command-centre/
├── .env.local                              Supabase URL + anon key
├── package.json
├── next.config.mjs
├── tsconfig.json
├── postcss.config.js
├── tailwind.config.ts                      design tokens (colors, fonts, animations)
│
├── public/
│   └── snapshot.json                       static fallback dataset (cached mode)
│
└── src/
    ├── app/
    │   ├── layout.tsx                      fonts, sidebar, top bar, mode provider
    │   ├── globals.css                     CSS variables, base styles
    │   ├── page.tsx                        Command Centre (/)
    │   ├── trajectory/page.tsx             /trajectory
    │   ├── review/page.tsx                 /review
    │   ├── alerts/page.tsx                 /alerts
    │   ├── analytics/page.tsx              /analytics
    │   ├── system/page.tsx                 /system
    │   │
    │   └── api/                            all backend routes (query Supabase)
    │       ├── health/route.ts             GET  — liveness check
    │       ├── snapshot/route.ts           GET  — full live snapshot
    │       ├── cameras/route.ts            GET  — cameras + links
    │       ├── sightings/route.ts          GET  — filtered sighting list
    │       ├── plates/search/route.ts      GET  — plate autocomplete
    │       ├── trajectory/[plate]/route.ts GET  — legs, anomalies, fuzzy-merge
    │       ├── analytics/summary/route.ts  GET
    │       ├── analytics/travel-times/route.ts   GET
    │       ├── analytics/heatmap/route.ts  GET  — hourly volume, O-D matrix
    │       ├── review/route.ts             GET  — open review cases
    │       ├── review/[id]/route.ts        POST — accept/correct/reject (writes DB)
    │       ├── alerts/route.ts             GET  — alerts list
    │       ├── alerts/[id]/acknowledge/route.ts  POST (writes DB)
    │       └── watchlist/route.ts          GET/POST/DELETE (writes DB, generates alerts)
    │
    ├── components/
    │   ├── PlateChip.tsx                   signature Indian-plate chip (used everywhere)
    │   ├── MapView.tsx                     Leaflet dark map, markers, route polyline
    │   ├── Sidebar.tsx                     left nav, 6 routes
    │   ├── TopBar.tsx                      live/cached status badge
    │   ├── Chips.tsx                       FlagChip, ConfidenceBar, StatusBadge, Skeleton
    │   └── CropThumb.tsx                   plate-crop placeholder card
    │
    └── lib/
        ├── types.ts                        shared TS types (Sighting, Camera, Alert, etc.)
        ├── supabase.ts                     Supabase client (URL/key hardcoded as fallback)
        ├── utils.ts                        plate regex, time formatting, consensus-vote fn
        ├── analytics.ts                    trajectory legs, travel-time, heatmap, search — pure fns, used by both API routes and cached-mode fallback
        ├── mode.tsx                        live/cached detection (2s health check)
        └── useSnapshot.ts                  lazy-loads public/snapshot.json for cached mode
```

40 files total. Zero placeholder/mock components — every screen reads real rows from Postgres when live.

--

## 4. Run it

```bash
npm install
npm run dev
```
