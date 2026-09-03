# Development and testing

## Prerequisites

- Node.js 18+
- npm 9+
- Python 3.10+ for the API and pipeline
- A Postgres connection only if testing the deployed/live database path; local API development uses SQLite by default

## Frontend workflow

```powershell
cd web/anpr-command-web
npm ci
npm run dev
```

The app is available at `http://localhost:3000`. With no reachable Supabase project, the UI should settle into cached mode and load `public/snapshot.json`.

Before committing frontend changes:

```powershell
npm run lint
npm run build
```

`next.config.mjs` currently allows the production build to ignore TypeScript build errors. Treat a successful build as necessary but not sufficient: review the browser behavior and run the focused checks for the area changed.

## API workflow

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r api/requirements.txt
python -m api.seed
python -m uvicorn api.main:app --reload --port 8000
```

The first run creates the default local SQLite file at `api/trace.db`. To seed from a particular snapshot:

```powershell
python -m api.seed path/to/snapshot.json
```

Run API tests with:

```powershell
python -m pytest api/test_api.py
```

## Pipeline workflow

The pipeline is GPU-oriented and processes video in batch. Install its dependencies separately from the API:

```powershell
python -m pip install -r pipeline/requirements.txt
python -m pipeline.process --cameras data/cameras.json --out data/
python -m pipeline.validate_snapshot data/snapshot.json
python pipeline/test_consensus.py
```

When integrating new pipeline output, validate the snapshot before copying it into `web/anpr-command-web/public/`. Keep timestamps, plate normalization, flag semantics, and asset paths aligned with the frozen contract.

## Tests and useful checks

```powershell
# All currently focused Python tests
python -m pytest api/test_api.py pipeline/test_consensus.py

# Validate the checked-in frontend fallback
python -m pipeline.validate_snapshot web/anpr-command-web/public/snapshot.json

# Inspect only documentation changes
git diff -- README.md docs/ pipeline/README.md web/anpr-command-web/README.md
```

## Change boundaries

The project was developed by multiple contributors with directory ownership. Respect the boundaries recorded in [`spec/00-START-HERE.md`](../spec/00-START-HERE.md). Shared contracts should be changed deliberately, with a version bump and communication to the other producers/consumers.

Documentation-only changes should not require modifying application code, lockfiles, generated databases, or generated media.

## Pull requests and commits

Keep commits focused and describe the user-visible or operational effect. A useful documentation change should answer:

1. What does this component do?
2. How do I run it locally?
3. What data or secrets does it require?
4. What happens when a dependency is unavailable?
5. How can I verify the change?
