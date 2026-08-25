# 04 — Design System & Screen Specs

**Version 1.0 — FROZEN.**

## Design thesis

The judge sees this alone, on an unknown device, with nobody explaining it. So the interface has to look like an instrument rather than a website — something an operator sits in front of at 2am, not something a startup launched.

The visual language is taken from the object the whole system is about: **the Indian number plate itself.** White ground with black condensed characters for private vehicles, yellow ground for commercial. That plate is the atomic unit of this product, so it becomes the atomic unit of the UI.

**Signature element: the plate chip.** Every plate string anywhere in the app — event feed, trajectory panel, review card, alert row, search result — renders as a miniature number plate: correct 4:1-ish proportion, hard 2px black border, 3px corner radius, black condensed mono characters on a white or amber ground. It is never plain text. One recurring object, used everywhere, instantly recognisable. Everything else on screen stays quiet so this reads.

An unreadable plate renders as a plate chip with a hatched grey ground and the word `UNREAD` — the absence is as visible as the presence. That single detail communicates the entire "failure-aware" thesis without a caption.

## Tokens

```css
--bg:        #0B1014;  /* night asphalt */
--surface:   #131A20;
--surface-2: #1A232B;
--border:    #26313B;
--text:      #E8EEF2;
--muted:     #8494A1;

--plate-white: #F2F4F0;  /* private plate ground */
--plate-amber: #E8B400;  /* commercial plate ground */
--plate-ink:   #0A0A0A;  /* plate characters */

--signal:    #4CC3C8;  /* primary accent — data, links, active states */
--warn:      #E8942E;  /* flags, review queue */
--danger:    #E0483B;  /* alerts, anomalies */
--ok:        #4FA96B;
```

Amber and red are reserved **exclusively** for flags and alerts. If they appear anywhere decorative, the alert state stops meaning anything.

## Type

| Role | Face | Use |
|---|---|---|
| Display | **Archivo Condensed**, 600 | Screen titles, KPI numbers, plate chip characters |
| Body | **Inter**, 400/500 | All prose, labels, buttons |
| Data | **JetBrains Mono**, 400 | Timestamps, coordinates, confidence values, IDs |

Load via `next/font`. Scale: 12 / 14 / 16 / 20 / 28 / 40. Titles are sentence case, never title case. Labels are uppercase `letter-spacing: 0.08em` at 12px — used sparingly, only for section eyebrows and flag chips.

## Layout

Persistent left rail, 64px collapsed with icon + label on hover, holding the six routes. Content fills the rest. Everything is dark; the map is the only large bright-ish surface and it uses a dark tile layer (CartoDB Dark Matter) so it doesn't blow out the page.

Motion: one orchestrated moment only — the trajectory polyline draws itself along the route over ~1.2 s when a plate is searched, with the camera markers lighting in sequence. Everything else is instant. Respect `prefers-reduced-motion` by rendering the full line immediately.

## Screens

Every route must be deep-linkable and must render meaningful content on first paint. **No empty states on initial load, ever.**

### `/` — Command Centre
- Full-bleed dark map, markers for all 8 cameras, subtle pulse on markers with recent activity.
- Top strip: four KPI tiles — vehicles seen, plates read, mean confidence, open alerts. Numbers in Archivo Condensed at 40px.
- Left of map: live event feed, newest first, each row = plate chip + camera name + relative time + confidence bar. Auto-scrolls slowly on load so it visibly moves.
- Bottom: horizontal timeline scrubber. Dragging it filters the map and feed by time window. This is the single most convincing interaction in the app — it makes the dataset feel like a recording rather than a table.
- First-visit overlay: three-step dismissible tour. Step 1 points at the scrubber, step 2 at the trajectory search, step 3 at the review queue. Stored in `localStorage`… **no** — Claude artifacts aside, this is a real Next.js app, so `localStorage` is fine here. Dismissal persists.

### `/trajectory`
- Search field, monospace input, uppercases as you type. Autocomplete from `/plates/search`.
- **Pre-filled example chips underneath: three real plates from the dataset that have 3+ sightings.** A judge must never face an empty search box.
- On search: map draws the animated polyline with direction arrows; right panel lists one card per sighting — plate chip, crop thumbnail, camera name, timestamp, confidence.
- Between cards, render the leg: `2.1 km · 36 s · 210 km/h implied`. If `anomaly` is true, the leg renders in `--danger` with the API's `anomaly_reason` printed in full and a `CLONE SUSPECTED` chip.
- If `fuzzy_merged_from` is non-empty, show a `FUZZY MERGE` note naming the variant reads that were stitched in. This is where the differentiator becomes visible.

### `/analytics`
- Travel-time table, congested pairs first, `delay_ratio` as a small inline bar. Congested rows in `--warn`.
- Hourly volume chart (recharts, bar).
- Per-camera density toggle on a small map.
- O-D matrix as a simple heat-shaded grid. Do not attempt a chord diagram.

### `/review` — the differentiator
- Grid of cards, one per open case. Card contains: crop image, the consensus plate chip, flag chip in `--warn` or `--danger`, and **the `raw_reads` array rendered as a per-frame list collapsing into the consensus result.** That visual — five noisy reads resolving into one clean plate — is the explanation of multi-frame consensus OCR. It replaces the presenter we don't have.
- Three actions: Accept, Correct, Reject. Correct opens an inline monospace field validated against the plate regex.
- In cached mode the actions are visible but disabled, with a tooltip: `Live backend unavailable — showing cached review cases.` Do not hide them; hidden features can't be judged.

### `/alerts`
- Watchlist hits, newest first: plate chip, status badge, camera, timestamp, crop, link to the trajectory.
- Watchlist management below: add a plate, see alerts generate.

### `/system` — carries the whole narrative
This route replaces the deck. It must be as polished as every other screen.
- Architecture diagram (inline SVG, hand-authored, matching the tokens — not an exported image).
- **Prototype vs target architecture table**, verbatim from `01-architecture.md`.
- **What is real / what is simulated**, stated plainly: real detection and OCR on real footage; simulated camera network geography; seeded mock registry standing in for VAHAN, which is a restricted government system with no public API.
- The measured OCR bake-off numbers.
- Known limitations, including that severely bent or non-planar plates are an open research problem we flag rather than silently miss.

Judges read this page. Being straight here is worth more than any additional feature.

## Quality floor

Responsive to 375px. Visible keyboard focus rings in `--signal`. `prefers-reduced-motion` respected. All images have alt text. No layout shift on data load — skeletons match final dimensions.
