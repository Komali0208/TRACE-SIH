# TRACE-SIH

## Multi-camera ANPR intelligence for trajectory reconstruction

TRACE-SIH is a prototype command centre for Automatic Number Plate Recognition (ANPR). It turns plate detections from multiple camera locations into a searchable operational view with vehicle trajectories, OCR review, watchlist alerts, and traffic analytics.

The project is designed to remain useful when a backend is unavailable: the Next.js frontend ships with a `snapshot.json` fallback and automatically uses it when its live health check fails. New snapshots should be validated against the shared contract before release.

> **Prototype disclosure:** the bundled dataset is synthetic/fixture data representing a simulated Bengaluru camera network. It is not a live government, traffic, VAHAN, or camera feed. The vehicle registry shown by the demo is explicitly mock data.

## What is included

- **Command centre (`/`)** — camera map, detection feed, KPIs, and a timeline view.
- **Trajectory reconstruction (`/trajectory`)** — search a plate, inspect sightings in time order, and review camera-to-camera legs, implied speeds, and anomaly signals.
- **OCR review (`/review`)** — inspect raw frame reads and accept, correct, or reject flagged sightings when a live backend is available.
- **Alerts and watchlist (`/alerts`)** — manage watchlist plates, view generated alerts, and acknowledge them.
- **Traffic analytics (`/analytics`)** — camera density, hourly volume, travel-time summaries, and origin-destination flow.
- **System view (`/system`)** — prototype architecture, data-source disclosure, and operational status.

## Architecture at a glance

```text
Video + camera metadata
        │
        ▼
Offline pipeline (pipeline/)
plate detection → tracking → OCR → multi-frame consensus → flags
        │
        ├── snapshot.json + crops + clips ──► static frontend assets
        │
        └── snapshot.json ──► database seed
                              │
                              ▼
                   Supabase/Postgres live data
                              │
                              ▼
              Next.js route handlers + command UI

Standalone FastAPI service (api/) exposes the same core contract for
local use, integration, and container deployment.
```

The current frontend calls its same-origin Next.js route handlers under `/api`. The FastAPI service is a separate backend surface; it is not automatically wired into the frontend by an environment variable in the current implementation.

## Repository map

| Path | Purpose |
| --- | --- |
| [`web/anpr-command-web`](web/anpr-command-web) | Next.js 14 frontend, UI components, route handlers, and bundled snapshot fallback |
| [`api`](api) | Standalone FastAPI service, SQLModel models, seed script, tests, and Dockerfile |
| [`pipeline`](pipeline) | Offline video processing, OCR consensus, annotation, and snapshot validation |
| [`spec`](spec) | Frozen architecture, API, data, design, and workflow contracts |
| [`data`](data) | Pipeline input/output boundary; large generated media is intentionally not committed here |
| [`scripts`](scripts) | Deployment helpers, including the Vercel monorepo flattening script |
| [`infra`](infra) | Infrastructure placeholders and deployment-owned configuration |

## Quick start: frontend

The frontend can be run in cached mode without a database. It uses the checked-in [`public/snapshot.json`](web/anpr-command-web/public/snapshot.json) when the live health check is unavailable.

### Prerequisites

- Node.js 18 or newer
- npm 9 or newer
- Git

### Run locally

```powershell
cd web/anpr-command-web
npm ci
npm run dev
```

Open <http://localhost:3000>.

For a live Supabase-backed frontend, create `web/anpr-command-web/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-public-anon-key
```

The public anon key is intended for browser use; never put a service-role key in a frontend environment variable or commit secrets to the repository.

Useful frontend commands:

```powershell
npm run lint
npm run build
npm run start
```

## Quick start: standalone FastAPI service

The API defaults to a SQLite database at `api/trace.db` when `DATABASE_URL` is not set. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r api/requirements.txt
python -m api.seed
python -m uvicorn api.main:app --reload --port 8000
```

The service is available at <http://localhost:8000>. Interactive OpenAPI documentation is available at `/docs`.

To use Postgres instead of local SQLite, set `DATABASE_URL` before starting the service:

```powershell
$env:DATABASE_URL = "postgresql://user:password@host:5432/database"
$env:FRONTEND_ORIGIN = "https://your-frontend.example.com"
python -m uvicorn api.main:app --reload --port 8000
```

The seed command accepts an optional snapshot path:

```powershell
python -m api.seed path/to/snapshot.json
```

## Data and static fallback

The shared data shape is defined in [`spec/02-data-contract.md`](spec/02-data-contract.md). The pipeline and API use the following conventions:

- timestamps are ISO 8601 UTC values;
- plate text is uppercase and contains no spaces or hyphens;
- coordinates are WGS84 decimal degrees;
- unknown values use `null`;
- flagged sightings are stored, not discarded;
- trajectories are derived from chronologically ordered sightings rather than stored separately.

The bundled fallback snapshot currently contains fixture data for eight cameras. A new pipeline run should produce `data/snapshot.json`; copy the resulting snapshot to `web/anpr-command-web/public/snapshot.json` before building the frontend. Crops and clips referenced by the snapshot belong under the corresponding `public/` asset directories when they are available.

## Deployment overview

### Vercel frontend

The repository is a monorepo: the Next.js app lives below `web/anpr-command-web`. [`vercel.json`](vercel.json) runs [`scripts/vercel-flatten-web.mjs`](scripts/vercel-flatten-web.mjs) during installation so Vercel can build the app from the repository root.

Configure the Supabase variables shown above in the Vercel project settings, then deploy the repository. The production build commands are:

```text
Install: node scripts/vercel-flatten-web.mjs && npm install
Build:   npm run build
```

### FastAPI container

[`api/Dockerfile`](api/Dockerfile) runs Uvicorn on port `7860`, which is suitable for container platforms such as Hugging Face Spaces. Provide `DATABASE_URL` as a platform secret and set `FRONTEND_ORIGIN` when the deployed frontend needs to be allowed by CORS.

### Keep-warm workflow

The optional [`.github/workflows/keepwarm.yml`](.github/workflows/keepwarm.yml) pings the deployed FastAPI `/health` endpoint every six hours. It requires a repository variable named `HF_SPACE_URL`.

## Documentation guide

- [Architecture](docs/ARCHITECTURE.md) — data flow, live/cached behavior, and service boundaries.
- [API reference](docs/API.md) — FastAPI endpoints, parameters, request bodies, and response conventions.
- [Development and testing](docs/DEVELOPMENT.md) — local workflows, validation, and contribution boundaries.
- [Operations](docs/OPERATIONS.md) — seeding, static assets, deployment checks, and troubleshooting.
- [Specification pack](spec/00-START-HERE.md) — authoritative frozen contracts and project context.
- [Pipeline guide](pipeline/README.md) — processing stages, consensus voting, output files, and integration points.

## Verification

Run the checks relevant to the area you changed:

```powershell
# Frontend
cd web/anpr-command-web
npm run lint
npm run build

# Backend and pipeline, from repository root
cd ../..
python -m pytest api/test_api.py pipeline/test_consensus.py
python -m pipeline.validate_snapshot web/anpr-command-web/public/snapshot.json
```

## Contribution boundaries

The original project workflow assigns ownership by directory. Before changing a contract or another team's area, read [`spec/00-START-HERE.md`](spec/00-START-HERE.md) and the relevant task brief. In particular, treat [`spec/02-data-contract.md`](spec/02-data-contract.md) and [`spec/03-api-contract.md`](spec/03-api-contract.md) as versioned interfaces.

## License

No license file is currently included in this repository. Confirm the intended license with the project maintainers before redistributing the code.
