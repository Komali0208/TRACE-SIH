# Operations guide

## Environment variables

### Frontend (`web/anpr-command-web/.env.local` or Vercel)

| Variable | Required for live frontend | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Browser-safe Supabase anon key |

Without a working live database, the frontend should show the bundled snapshot in cached mode. Never use a Supabase service-role key in `NEXT_PUBLIC_*` variables.

### FastAPI (`api/` or container platform)

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | No | Postgres connection string; omitted means local SQLite at `api/trace.db` |
| `FRONTEND_ORIGIN` | No | Additional exact origin allowed by CORS |

The Docker image exposes port `7860` and starts `uvicorn main:app`.

### GitHub Actions

The keep-warm workflow expects the repository variable `HF_SPACE_URL`. It requests `${HF_SPACE_URL}/health` and fails if the response is not HTTP 200.

## Seed and refresh procedure

1. Produce or obtain a schema-valid `snapshot.json`.
2. Run the validator:

   ```powershell
   python -m pipeline.validate_snapshot path/to/snapshot.json
   ```

3. Seed the FastAPI database if the service uses the local/API seed path:

   ```powershell
   python -m api.seed path/to/snapshot.json
   ```

4. Copy the snapshot to `web/anpr-command-web/public/snapshot.json` for the frontend fallback.
5. Copy referenced crops and clips into the frontend's `public/` asset tree.
6. Confirm every relative asset URL resolves and that clips meet the deployment-size limit.
7. Build and smoke-test the frontend.

Seeding uses `session.merge`, so records in the input snapshot are inserted or updated by their keys. Treat the input snapshot as the source of truth for a refresh and review the database state before running a production seed.

## Deployment checks

### Frontend

- `npm run build` succeeds from `web/anpr-command-web`.
- Supabase URL and anon key are configured in the deployment environment.
- The deployed site loads the dashboard without requiring the backend to be healthy.
- `/api/health` returns success when the live database is available.
- A backend outage changes the status to cached and disables write actions.

### FastAPI

- The service listens on the platform-provided port; the included Dockerfile uses `7860`.
- `DATABASE_URL` points to a persistent Postgres database in production.
- `FRONTEND_ORIGIN` is set when an exact production origin must be allowed.
- `GET /health` returns HTTP 200.
- `GET /snapshot` and `GET /cameras` return non-null arrays after seeding.
- Logs do not contain database credentials or public user data beyond what is needed for diagnosis.

## Troubleshooting

### The frontend shows cached mode

This means the frontend health check did not receive a successful response within two seconds. Check the browser network panel for `/api/health`, verify Supabase variables, and confirm the database contains the expected `app_meta` row. Cached mode is an intentional read-only fallback, not necessarily a frontend failure.

### The API starts but has no data

Run `python -m api.seed` and inspect the printed row counts. If a custom snapshot is used, pass its explicit path and validate it first.

### The API cannot connect to Postgres

Check `DATABASE_URL`, network allowlists, SSL requirements, and whether the database is reachable from the deployment platform. Unset `DATABASE_URL` locally to return to the SQLite path.

### Media is missing

The APIs return relative paths; they do not serve crops or videos. Verify that the referenced files exist below the frontend's `public/` directory and that the browser can request them from the deployed frontend origin.

### Keep-warm job fails

Confirm the repository variable `HF_SPACE_URL` is present, has no trailing-path mistake, and that `${HF_SPACE_URL%/}/health` returns HTTP 200 within 30 seconds.

## Data and privacy note

This repository describes a surveillance-oriented prototype. The bundled registry records are mock data, and the camera network is simulated. Any production deployment would require a formal data-governance review, access controls, retention policy, audit logging, and legal authorization before processing real vehicle or personally identifying data.
