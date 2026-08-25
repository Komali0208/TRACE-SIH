# Task C — Frontend
**Owner: Karthik · Branch: `feat/web` · Scope: `web/` only**

> **Agent scope fence — paste this at the top of every prompt:**
> Only create or modify files under `web/`. Do not touch `api/`, `pipeline/`, `specs/`, `data/`, or any root-level file. If you think a change is needed elsewhere, describe it instead of making it.

You own everything the judge actually sees. There is no presentation and nobody in the room explaining anything — so the interface has to explain itself. That constraint should drive every decision you make.

Read `04-design-system.md` in full, twice. It contains the visual direction and per-screen specs; implement it exactly rather than reaching for defaults. Read `03-api-contract.md` for shapes.

You are never blocked. Copy `specs/fixtures/snapshot.example.json` to `web/public/snapshot.json` at hour 0 and build the entire app against it.

---

## The rule that shapes the architecture

**Every screen must render correctly with the API completely unreachable.**

On load: read `/snapshot.json` from the static bundle and render immediately. In parallel, `fetch` `/health` with a 2000 ms `AbortController` timeout.

- Resolves in time → live mode. Fetch fresh data, enable write actions. Status chip: `Live`.
- Times out or errors → stay on the snapshot. Write actions rendered but **disabled with a tooltip**, not hidden. Status chip: `Cached dataset`.

One set of TypeScript types serves both sources — the API and the snapshot return identical shapes. If you find yourself writing an adapter, the contract has been broken; report it rather than working around it.

**No loading spinner on first paint. No error screen. Ever.** A judge who opens the link to a spinner closes the tab, and you won't be there to hit refresh.

## Build order

| Hours | What |
|---|---|
| 0–1 | `create-next-app` (App Router, TS, Tailwind), fonts via `next/font`, tokens from `04-design-system.md`, left rail with six routes |
| 1–3 | Snapshot loading + live/cached mode detection + TS types + **the plate chip component** |
| 3–8 | `/` Command Centre: map, camera markers, KPI tiles, event feed, timeline scrubber |
| 8–14 | `/trajectory`, `/review`, `/alerts`, `/analytics`, evidence video player |
| 14–19 | `/system`, guided tour overlay, mobile pass, polish |

## Build the plate chip first

Before any screen. Every plate string in the app renders through it: event feed, trajectory panel, review card, alert row, search result. It is the signature element of the design and the thing that makes the app look designed rather than assembled.

Miniature Indian number plate — hard 2px black border, 3px radius, black Archivo Condensed characters on `--plate-white` (private) or `--plate-amber` (commercial). Unreadable plates render with a hatched grey ground and the word `UNREAD`, so an OCR failure is as visible on screen as a success. That one detail communicates the entire failure-aware thesis without a caption.

## Screens that need special care

**Timeline scrubber** (`/`) — dragging it filters map and feed by time window. This is the most convincing interaction in the app; it makes the dataset feel like a recording rather than a table. Worth more than a whole extra screen.

**`/trajectory`** — pre-fill three example plate chips beneath the search box, read from `meta.hero_plates` in the snapshot. **A judge must never face an empty search box.** Between sighting cards, render the leg: `2.1 km · 36 s · 210 km/h implied`. Anomalous legs in `--danger` with the API's `anomaly_reason` printed in full.

**`/review`** — the differentiator, and the reason it works without a presenter. Each card renders the `raw_reads` array as a per-frame list visually collapsing into the consensus plate. Five noisy reads resolving into one clean plate *is* the explanation of multi-frame consensus OCR. Get this one right and it does the job the deck would have done.

**`/system`** — as polished as everything else. Judges read it. Content is specified in `04-design-system.md`; Daksha supplies the text.

## Quality floor

375px responsive — check on the Vercel preview from an actual phone, not devtools. Visible focus rings. `prefers-reduced-motion` respected. Skeletons match final dimensions so nothing shifts.

## Traps

- Building against the API instead of the snapshot, then discovering the fallback doesn't work at hour 18
- Hiding disabled actions in cached mode — hidden features can't be judged
- Using amber or red decoratively — it destroys the meaning of the alert states
- Leaving `/system` to the end and shipping it unstyled. With no deck, it carries the entire narrative
- Testing only on desktop wifi
