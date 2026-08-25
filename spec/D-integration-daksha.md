# Task D — Integration, Data, Deployment, Narrative
**Owner: Daksha · Branch: `feat/infra` · Scope: `specs/`, `data/`, `infra/`, root config**

You don't take a build surface. Integration owner plus deployment owner plus contract owner plus narrative owner is a full job in 24 hours, and if the contract drifts you are the only person positioned to catch it before it costs six hours.

---

## H0 · Before anyone writes feature code

One commit to `main`:

- Directory skeleton with `.gitkeep` in each
- **`.editorconfig`, `.prettierrc`, `ruff.toml`** — these cannot be added later. Three AI coding tools format differently; without shared configs you get 400-line diffs on 3-line changes and every merge conflicts. This is the most common way parallel AI-assisted builds fall apart.
- `.gitignore`: `__pycache__/`, `.venv/`, `node_modules/`, `.next/`, `*.onnx`, `.env*`
- The whole `specs/` folder, fixtures generated and committed

Then confirm in the group chat that all three teammates have cloned, installed, and can run their skeleton. Someone's environment will be broken. Better to find it now.

## H1–3 · Deploy the skeleton (the most important thing you do)

Before any feature exists:

1. **Neon** project, database created, connection string saved
2. **Hugging Face Space**, Docker SDK, Komali's container serving `/health` on port 7860, `DATABASE_URL` in Space secrets
3. **Vercel** connected to `main`, root directory `web/`, `NEXT_PUBLIC_API_BASE` set to the Space URL
4. **CORS verified end to end** — open the Vercel URL, confirm the browser can reach `/health` without a CORS error
5. **GitHub Actions keep-warm cron**, every 6 hours, pinging `/health`. Free CPU Spaces sleep after ~48h idle; this prevents it

**Gate: at hour 3 there is a public URL that renders.** If not, everyone stops feature work until there is. Teams that defer deployment to hour 20 do not deploy.

## H3–8 · The footage

**Moved. See `08-data-sourcing.md` — this now happens BEFORE the build clock starts, not during it.**

Data sourcing cannot be parallelised, cannot be given to an agent, and blocks Sachidanand completely. Doing it inside the build window was a scheduling error. Complete it the day before.

Summary of what you produce:
- ~50 labelled plate crops for Sachidanand's bake-off
- 4 filmed locations, 3–4 minutes each, plates legible
- One staged repeat vehicle across 3 locations
- `data/cameras.json` with real coordinates and real road distances

Full instructions in `08-data-sourcing.md`.

## H8–19 · Integration and narrative

- Run the pipeline on real footage, regenerate `snapshot.json`, seed Neon, **copy the snapshot to `web/public/`**. This last step is easy to forget and silently leaves the fallback stale
- Commit everything in `data/`. **Only you commit binaries** — this is what keeps binary merge conflicts at zero
- Run the three checkpoint merges in order: `feat/infra` → `feat/pipeline` → `feat/api` → `feat/web`
- Write the `/system` content and hand it to Karthik: architecture diagram, prototype-vs-target table, what's real / what's simulated, Sachidanand's measured OCR numbers, known limitations

### On `/system`, state these plainly

- Real detection and OCR, running on real footage, with measured accuracy
- Simulated camera network geography — segmented public footage with assigned coordinates
- Seeded mock registry standing in for VAHAN, which is a restricted government system with no public API. Never imply otherwise
- Severely bent or non-planar plates are an open research problem. We flag them rather than silently missing them — that's the design principle, not a gap to hide

With no deck and no presenter, this page is the entire argument. Being straight here is worth more than any additional feature, and a judge who catches an overclaim discounts everything else on the site.

## H19+ · Verification

- **Open the URL from four devices on four networks**, including mobile data. Not just campus wifi
- **Test cold**: private window, API deliberately stopped, confirm cached mode renders everything
- **Record a full screen-capture walkthrough** as insurance
- README and submission text

## Your standing job

At every checkpoint, before anything else: **is the deployed URL working right now?** Not localhost. The URL. If no, that is the only task anyone has until yes.

And watch for contract drift. When Komali says "I just renamed that field, it reads better" — that is the moment six hours evaporate. The answer is always: message the group, bump the version, or don't do it.
