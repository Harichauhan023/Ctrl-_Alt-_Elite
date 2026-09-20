# GeoReady-AI

Site readiness analysis on a map. You click a location, we pull the geographic features
for that spot, score it, run it through a trained model, and then have Gemini explain
the result using our own knowledge base.

Built for PS-2.

The one rule we keep coming back to: nothing on screen is faked. If the UI shows a score
of 84, that number came back from the API. No `const score = 84;` anywhere in the
frontend. If you find one, delete it.

## How it works

```
click on map
  -> POST /api/analyze
       feature extraction (land use, accessibility, population, risk, proximity)
       deterministic weighted score
       ML prediction (RandomForest)
  -> POST /api/explain
       retrieve relevant chunks from rag/documents
       send analysis + chunks to Gemini
       return explanation + the sources it used
```

Two numbers come back for every location: the deterministic score, which is a weighted
formula you can tune from the sliders in the UI, and the ML prediction, which comes from
the trained model. They're meant to be independent. If they disagree a lot, that's
interesting, not a bug.

## Tech stack

- **Frontend** — MapLibre GL JS, npm toolchain
- **Backend** — FastAPI, Python 3.12, Uvicorn
- **Database** — Postgres + PostGIS for geometry, pgvector for embeddings
- **ML** — scikit-learn RandomForestRegressor, joblib
- **Embeddings** — all-MiniLM-L6-v2, runs locally so retrieval doesn't cost an API call
- **LLM** — Gemini, with a provider manager that rotates between keys
- **Infra** — Docker Compose, GitHub Actions
- **Tests** — pytest for backend, `npm run build` for frontend

## Folder structure

```
backend/          FastAPI app, feature extraction, scoring, Gemini provider manager
frontend/         MapLibre dashboard
ml/               train.py, predict.py, evaluate.py, models/
rag/              documents/, ingest.py, test_retrieval.py
data/             datasets
scripts/          pipeline + helper scripts
tests/backend/    pytest suite
docs/
infra/
.github/workflows/ci.yml
docker-compose.yml
.env.example
```

## Team ownership

- **M1** — `backend/`, `tests/backend/`
- **M2** — `frontend/`
- **M3** — `ml/`, `rag/`, `data/`, `scripts/`
- **M4** — root files, `docs/`, `infra/`, Docker, CI

Stay in your own folders. If something needs changing in someone else's area, ask them
first instead of editing it yourself. Saves a lot of conflicts.

## Setup

You need Python 3.12, Node, Docker Desktop and Git.

```powershell
git clone https://github.com/<owner>/geoready-ai.git
cd geoready-ai
```

If you got the bundle instead of repo access:

```powershell
cd D:\Kaydesar
git clone .\GeoReady-AI.bundle geoready-ai
cd geoready-ai
git log --oneline --decorate -5
```

You should see the existing history in that log. Don't run `git init` in that folder —
it starts a second history and undoing it is a pain.

Copy the env file and fill in your keys:

```powershell
copy .env.example .env
```

`.env` is gitignored. Keep it that way.

Database:

```powershell
docker compose up -d
docker compose ps
```

Backend:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Frontend:

```powershell
cd frontend
npm install
cd ..
```

## Running the project

Three terminals.

```powershell
docker compose up -d
```

```powershell
py -3.12 -m uvicorn backend.app.main:app --reload
```

```powershell
cd frontend
npm run dev
```

Swagger is at http://127.0.0.1:8000/docs. Easier than the UI when you just want to check
an endpoint.

## Environment variables

`.env.example`:

```
DATABASE_MODE=auto

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=geoready
POSTGRES_USER=geoready
POSTGRES_PASSWORD=

GEMINI_PROVIDER_1_API_KEY=
GEMINI_PROVIDER_2_API_KEY=
GEMINI_PROVIDER_3_API_KEY=
GEMINI_PROVIDER_4_API_KEY=

GEMINI_MODEL=

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

There are four Gemini key slots because the free tier rate limits quickly during a demo.
The provider manager rotates through whichever ones are filled in. One key is enough for
development.

`DATABASE_MODE=auto` lets the backend fall back when Postgres isn't running, so frontend
work doesn't need Docker open the whole time.

Real keys never go into `.env.example`.

## ML and RAG

### ML

```powershell
py -3.12 ml\train.py
```

Reads the data, builds the feature table, trains a RandomForestRegressor and writes
`ml/models/site_readiness_model.joblib`.

```powershell
py -3.12 ml\predict.py
py -3.12 ml\evaluate.py
```

`evaluate.py` writes R2, MAE and RMSE to `ml/models/metrics.json`. Those numbers go into
the slides, so they have to come from an actual run. Don't type values into that file by
hand.

`predict.py` has to load the joblib file. If a prediction is coming out of some formula
instead of the model, that's a bug worth fixing before the demo.

### RAG

Knowledge lives in `rag/documents/` as markdown:

```
ev_charging.md
retail.md
warehouse.md
scoring.md
landuse.md
environmental_risk.md
accessibility.md
```

Ingest chunks them, embeds with all-MiniLM-L6-v2 and stores everything in pgvector:

```powershell
py -3.12 rag\ingest.py
py -3.12 rag\test_retrieval.py
```

The retrieval test should return something like:

```
Query: EV charging accessibility

EV Charging...
Accessibility...
Land Use...
```

Empty results usually mean the vector table never got populated. Re-run ingest, and
check that `rag/documents/` actually got committed.

Whatever comes back is shown in the sources panel in the UI, so every explanation can be
traced back to a document.

## Tests

From the repo root:

```powershell
py -3.12 -m pytest -q
```

33 passing right now, more as people add tests. If it's red, fix it before you push.

Frontend just needs to build:

```powershell
cd frontend
npm run build
cd ..
```

CI runs both of these on every PR, so a broken branch will show up there anyway.

## Git workflow

GitHub is the only source of truth. No zips, no shared drives, no copying folders off
someone's laptop.

Set your identity once, with your own details:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Before starting anything:

```powershell
git checkout main
git pull origin main
git checkout -b your/branch
```

The pull matters. Branch off a stale main and you'll be fixing conflicts later for no
reason.

Branches:

```
backend/core-integration      M1
frontend/dynamic-dashboard    M2
ml/rag-pipeline               M3
infra/demo-ready              M4
```

When you're done:

```powershell
git add -A
git commit -m "feat: whatever you did"
git push -u origin your/branch
```

Open the PR and assign your reviewer. Rotation:

```
M1 reviews M2
M2 reviews M3
M3 reviews M4
M4 reviews M1
```

Nobody reviews their own PR, nobody merges their own PR.

If you're the reviewer, actually open the changed files. Then approve, squash and merge,
delete the branch. After any merge everyone runs:

```powershell
git checkout main
git pull origin main
```

Commit messages we're using:

```
feat: integrate geospatial analysis backend        M1
feat: connect dynamic geospatial dashboard         M2
feat: add ML prediction and RAG pipeline           M3
ci: make project demo-ready                        M4
```

### Don't

- `git push origin main` — direct pushes to main are off limits unless we all agree it's
  an emergency
- commit `.env`, API keys, passwords, `node_modules`, or large generated files
- run `git init` in the clone
- make five branches for small edits. One branch per person for your chunk of work

### If something goes wrong

**Forgot to pull before branching.** Checkout main, pull, recreate the branch.

**Uncommitted changes and you need to switch.** Run `git status` first. If the work
belongs to what you're doing, commit it as `wip: save current work`. If it doesn't, sort
it out before switching instead of jumping branches.

**Merge conflict.** `git status`, open the conflicted files, fix them properly. Don't
delete files to make the conflict go away — that's how work disappears. Then `git add -A`,
commit, push.

**Branch won't delete after merge.** Try `git branch -d name`. If Git says it isn't
fully merged locally, confirm the PR really did merge on GitHub, then use `-D`.

## Demo checklist

Worth walking through this before showing it to anyone:

1. Map loads with a real basemap
2. Click site A — features, score and ML prediction come back
3. Click site B somewhere else — the numbers change
4. Generate explanation — goes through RAG, then Gemini
5. Explanation lists the source documents it used
6. Move the population weight from 25% to 35% — deterministic score changes

Then check the repo:

```powershell
git status
git branch
git log --oneline --decorate -10
```

Clean tree, on main, all four contributions in the log. On GitHub, double-check there's
no `.env`, no keys, and nothing huge that got committed by accident.

## Common problems

**Git not installed** — `winget install --id Git.Git -e --source winget`, then reopen
PowerShell.

**Postgres won't start** — `docker compose logs db`. Usually port 5432 is already taken
by a local Postgres install.

**Pytest import errors** — you're probably not in the repo root, or the venv isn't
activated.

**Model file missing** — run `py -3.12 ml\train.py`.

**Gemini 429** — out of quota on that key. Add another one to `.env`.

**Frontend build fails after a pull** — delete `node_modules` and `npm install` again.

## Final workflow

One repo, one main branch, four people:

```
M1 backend
M2 frontend      ->  main
M3 ML + RAG
M4 infra
```

Everything gets in through branch, commit, push, PR, review, merge. Nobody works
directly on main.
