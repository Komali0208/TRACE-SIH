# TRACE — Spec Pack

**Project:** TRACE (Trajectory Reconstruction & ANPR Command Engine)
**Problem statement:** SIH 2026 PS 26127 — City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics (BEL, Software)
**Build window:** ~24 working hours, 4 people
**Deliverable:** a deployed public URL. No live presentation. Judges browse unattended.

---

## Read this first

This is a **spec-driven build**. Every file in `specs/` is frozen before feature code starts. If you need something the spec doesn't cover, you ask in the group chat — you do not improvise a field name.

The reason is mechanical, not bureaucratic: four people are running four AI coding agents in parallel. Agents are excellent at writing code and terrible at guessing what someone else's agent decided to call a column. The spec is the shared memory the agents don't have.

## Reading order

| # | File | Who must read it |
|---|---|---|
| 01 | `01-architecture.md` | Everyone |
| 02 | `02-data-contract.md` | Everyone |
| 03 | `03-api-contract.md` | Komali, Karthik, Daksha |
| 04 | `04-design-system.md` | Karthik, Daksha |
| 05 | `05-git-workflow.md` | Everyone |
| 06 | `06-timeline.md` | Everyone |
| — | `tasks/<your-letter>-*.md` | You, in full, twice |

Then open your own task brief and paste it into your agent as context. The task briefs are written to be usable as prompts.

## Ownership map — this is a hard boundary

| Person | Owns (exclusive write access) |
|---|---|
| Sachidanand | `pipeline/` |
| Komali | `api/` |
| Karthik | `web/` |
| Daksha | `specs/`, `data/`, `infra/`, root config files, `README.md` |

**Nobody edits a directory they don't own.** If you need a change elsewhere, message the owner. This single rule is what prevents merge conflicts; everything in `05-git-workflow.md` is secondary to it.

Every prompt you give your coding agent must open with a scope fence:

> Only create or modify files under `api/`. Do not touch `web/`, `pipeline/`, `specs/`, `data/`, or any root-level file.

Agents will happily "helpfully" refactor your teammate's directory if you don't say this.

## The three rules that matter most

1. **The contract is frozen.** `02-data-contract.md` and `03-api-contract.md` do not change without a message in the group chat and a version bump at the top of the file.
2. **Build against fixtures, not against each other.** `specs/fixtures/snapshot.example.json` exists so Komali and Karthik start at minute 30 instead of hour 6. Nobody waits for the pipeline.
3. **Deploy at hour 3, not hour 20.** A skeleton deployed early is a build that ships. Deployment left to the end is a build that doesn't.

## What "done" means

At hour 19 (feature freeze), a stranger opens the URL on a phone in a different city, with no explanation, and within four minutes understands: what the system does, that the detections are real, and that it handles its own failure cases visibly. If that's true, we shipped. If it's true *and* the extras work, we did well.
