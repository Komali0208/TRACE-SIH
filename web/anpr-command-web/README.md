# TRACE-SIH frontend

This directory contains the Next.js 14 frontend for TRACE-SIH: the command centre, trajectory view, OCR review queue, alerts/watchlist, analytics, and system pages.

## Run locally

```powershell
npm ci
npm run dev
```

Open <http://localhost:3000>.

The app performs a short `/api/health` check. If the live Supabase-backed route handlers are unavailable, it loads [`public/snapshot.json`](public/snapshot.json) and switches to read-only cached mode.

For live data, create `.env.local` in this directory:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-public-anon-key
```

## Commands

```powershell
npm run dev
npm run lint
npm run build
npm run start
```

## Important directories

- `src/app/` — pages and same-origin API route handlers
- `src/components/` — reusable dashboard components
- `src/lib/` — Supabase client, types, analytics, mode detection, and snapshot fallback loading
- `public/` — static snapshot and generated media assets

See the repository-level [README](../../README.md), [API reference](../../docs/API.md), and [architecture guide](../../docs/ARCHITECTURE.md) for the complete system documentation.
