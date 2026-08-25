# 05 — Git Workflow

## Repository layout

```
/
├── specs/          Daksha only — frozen contracts
├── pipeline/       Sachidanand only
├── api/            Komali only
├── web/            Karthik only
├── data/           Daksha only — generated artefacts
├── infra/          Daksha only — Dockerfile, HF Space config, GH Actions
├── .editorconfig   Daksha only
├── .prettierrc     Daksha only
├── ruff.toml       Daksha only
└── README.md       Daksha only
```

## Hour 0 — before any feature code

Daksha commits, in one commit, to `main`:

- The full directory skeleton with a `.gitkeep` in each
- `.editorconfig`, `.prettierrc`, `ruff.toml`
- `.gitignore` covering `__pycache__/`, `.venv/`, `node_modules/`, `.next/`, `*.onnx`, `.env*`
- The entire `specs/` folder including generated fixtures

**The formatter configs are not optional and cannot be added later.** Cursor, Antigravity and opencode each format Python and TypeScript differently. Without shared configs you will get 400-line diffs on 3-line changes and every merge will conflict. This is the single most common way parallel AI-assisted builds fall apart.

## Branches

| Person | Branch |
|---|---|
| Sachidanand | `feat/pipeline` |
| Komali | `feat/api` |
| Karthik | `feat/web` |
| Daksha | `feat/infra` |

Long-lived, one each, for the whole build. Do not create feature-per-task branches — with a 24-hour window the overhead outweighs the benefit.

## Cadence

- **Commit every 30–45 minutes.** Working or not, commit. `wip: consensus voting, not yet passing` is a perfectly good message at 4am.
- **Push at minimum every hour.** An unpushed branch does not exist. If your laptop dies at hour 14 with six hours of unpushed work, the project is over.
- **Merge to `main` at each checkpoint only** — hours 8, 14, 19. Not continuously. Batching merges to three known moments means conflicts happen when everyone is awake and looking, not at random.

Commit message prefixes: `feat:`, `fix:`, `wip:`, `chore:`, `data:`. Nothing stricter — this is a hackathon, not a release train.

## Merging at a checkpoint

Everyone, at the same time, in this order:

```bash
git add -A && git commit -m "wip: checkpoint N"
git push origin feat/<yours>
git fetch origin
git rebase origin/main
# resolve anything (there should be nothing — see below)
git push --force-with-lease origin feat/<yours>
```

Then Daksha merges the four branches into `main` in order: `feat/infra` → `feat/pipeline` → `feat/api` → `feat/web`. Backend before frontend so that if the API shape drifted, Karthik rebases onto the corrected version rather than the reverse.

## Conflicts

If ownership is respected, **conflicts are structurally impossible** — no two people ever write to the same file. When one appears, it means either someone crossed a boundary or it's one of these three known cases:

| File | Resolution |
|---|---|
| `web/package-lock.json` | Delete it, `npm install`, commit the regenerated file. **Never hand-merge a lockfile.** |
| `api/requirements.txt` | Only Komali edits this. If it conflicts, take Komali's version. |
| `data/snapshot.json` and other binaries | Only Daksha commits to `data/`. `git checkout --theirs` and regenerate. |

Sachidanand does not commit generated data. He hands the output files to Daksha (shared drive, Slack, scp — anything), and Daksha commits them. This keeps binary conflicts at zero.

If you hit a conflict you don't understand: **stop and message the group.** Do not let an AI agent resolve a merge conflict unsupervised — agents routinely resolve them by deleting one side.

## Rules for the agents

Every prompt opens with a scope fence:

> Only create or modify files under `<your-dir>/`. Do not touch any other directory or any root-level file. If you believe a change is needed elsewhere, describe it instead of making it.

And when the contract is relevant, paste the relevant spec file into context rather than describing it. The specs were written to be pasted.

## Deployment triggers

- `main` → Vercel production. Auto-deploys on merge.
- `feat/web` → Vercel preview URL. Karthik gets a live preview per push, which is how he checks mobile without a device.
- API deploys to the HF Space by pushing the `api/` subtree — Daksha runs this at each checkpoint, not continuously.

## Hour 19: feature freeze

After feature freeze, `main` accepts **fixes only**. A fix is a change that makes an existing feature work. Anything that adds a capability is out, however small and however tempting. The last five hours are for the deploy being verified from four different devices and networks, not for one more heatmap.
