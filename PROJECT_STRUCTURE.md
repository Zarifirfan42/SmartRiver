# SmartRiver — Project Structure

Predictive River Pollution Monitoring System — Clean Architecture

## Root layout

```
SmartRiver/
├── data_management/          # Module 1: Auth, RBAC, datasets, prediction logs
│   ├── services/
│   ├── controllers/
│   ├── models/
│   └── utils/
├── data_preprocessing/       # Module 2: Clean, normalize, WQI, features
│   ├── services/
│   ├── controllers/
│   ├── models/
│   └── utils/
├── ml_engine/                # Module 3: RF, LSTM, Isolation Forest
│   ├── services/
│   ├── controllers/
│   ├── models/
│   └── utils/
├── visualization_alert/      # Module 4: Dashboard, charts, map, alerts, export
│   ├── services/
│   ├── controllers/
│   ├── models/
│   └── utils/
├── backend/                  # FastAPI app (wires the 4 modules)
├── frontend/                 # React + TailwindCSS
├── ml_models/                # Persisted ML artifacts
├── database/                 # Migrations, schema
├── datasets/                 # Uploaded CSV storage
└── docs/                     # SRS, architecture, API
```

## Module layers (each module)

- **controllers** — HTTP/API (FastAPI routers)
- **services** — Business logic
- **models** — Domain and persistence models (ORM, schemas)
- **utils** — Helpers, validators, formatters

## Running the project

- **Backend:** From project root, ensure `data_management`, `data_preprocessing`, `ml_engine`, `visualization_alert` are on `PYTHONPATH` (or run from root). Then: `cd backend && uvicorn app.main:app --reload`
- **Frontend:** `cd frontend && npm install && npm run dev`
- **Database:** Use `docs/database_schema.sql` or Alembic; set `DATABASE_URL` in `backend/.env`

## Docs

See `docs/README.md` for SRS, architecture, API, ML workflow, and UI pages.
