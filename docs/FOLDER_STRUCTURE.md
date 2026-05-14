# SmartRiver — Folder Structure

Recommended layout for a clean, modular codebase.

## Implemented structure (4 modules at root)

See **PROJECT_STRUCTURE.md** in the repo root for the current layout: `data_management/`, `data_preprocessing/`, `ml_engine/`, `visualization_alert/` (each with services, controllers, models, utils), plus `backend/`, `frontend/`, `ml_models/`, `database/`, `datasets/`.

---

## Detailed layout (reference)

```
SmartRiver/
├── backend/                          # Python FastAPI
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app, CORS, router includes
│   │   ├── config.py                  # Settings (env, paths)
│   │   ├── dependencies.py            # Common deps (DB session, current user)
│   │   │
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # POST register, login, GET me
│   │   │   ├── service.py             # Hash, verify, create user
│   │   │   ├── deps.py                # get_current_user, require_admin
│   │   │   └── schemas.py             # Login, Register, Token, User
│   │   │
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # CRUD datasets, upload, prediction-logs
│   │   │   ├── service.py             # Upload file, parse CSV, store metadata
│   │   │   ├── repository.py          # DB access for datasets, readings
│   │   │   └── schemas.py             # Dataset, DatasetCreate, etc.
│   │   │
│   │   ├── preprocessing/
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # POST run preprocessing
│   │   │   ├── service.py             # Orchestrate: load → clean → WQI → features
│   │   │   ├── wqi.py                 # DOE WQI calculation
│   │   │   └── schemas.py             # PreprocessOptions, PreprocessResult
│   │   │
│   │   ├── ml/
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # Train/predict for classification, forecast, anomaly
│   │   │   ├── pipeline.py            # Load preprocessed data, call models
│   │   │   ├── classification.py      # Random Forest train/predict
│   │   │   ├── forecasting.py         # LSTM train/predict
│   │   │   ├── anomaly.py             # Isolation Forest detect
│   │   │   └── schemas.py             # Train/Predict request/response
│   │   │
│   │   ├── viz/
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # Dashboard summary, river-health, time-series, forecast, map
│   │   │   └── service.py             # Aggregate data for dashboard
│   │   │
│   │   ├── alerts/
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # GET list, PATCH read
│   │   │   └── service.py             # Create alert from anomaly, list, mark read
│   │   │
│   │   ├── reports/
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # POST export (CSV/PDF)
│   │   │   └── service.py             # Generate CSV/PDF from data
│   │   │
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── dataset.py
│   │   │   ├── reading.py
│   │   │   ├── prediction_log.py
│   │   │   └── alert.py
│   │   │
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── session.py             # get_db, engine
│   │       └── base.py                # Base model
│   │
│   ├── tests/
│   │   ├── conftest.py                # Fixtures (client, db, user)
│   │   ├── test_auth.py
│   │   ├── test_datasets.py
│   │   └── ...
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/                          # React + TailwindCSS
│   ├── public/
│   │   ├── index.html
│   │   └── ...
│   ├── src/
│   │   ├── index.jsx
│   │   ├── App.jsx
│   │   ├── api/
│   │   │   ├── client.js              # Axios instance + auth header
│   │   │   ├── auth.js
│   │   │   ├── datasets.js
│   │   │   ├── preprocessing.js
│   │   │   ├── ml.js
│   │   │   ├── dashboard.js
│   │   │   ├── alerts.js
│   │   │   └── reports.js
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.jsx       # Sidebar + header + outlet
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── Header.jsx
│   │   │   ├── charts/
│   │   │   │   ├── TimeSeriesChart.jsx   # Plotly or Chart.js
│   │   │   │   ├── ForecastChart.jsx
│   │   │   │   └── StatusPieChart.jsx
│   │   │   ├── map/
│   │   │   │   └── RiverMap.jsx          # Leaflet
│   │   │   ├── alerts/
│   │   │   │   ├── AlertsPanel.jsx
│   │   │   │   └── AlertToast.jsx
│   │   │   └── common/
│   │   │       ├── Button.jsx
│   │   │       ├── Card.jsx
│   │   │       ├── Table.jsx
│   │   │       └── ProtectedRoute.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── RiverHealthPage.jsx
│   │   │   ├── UploadDatasetPage.jsx     # Admin
│   │   │   ├── DatasetListPage.jsx       # Admin
│   │   │   ├── RunProcessingPage.jsx     # Admin: run preprocess + ML
│   │   │   ├── AlertsPage.jsx
│   │   │   └── ExportReportPage.jsx
│   │   │
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   │
│   │   ├── hooks/
│   │   │   └── useAuth.js
│   │   │
│   │   └── styles/
│   │       └── index.css                # Tailwind imports
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js                  # or CRA
│   └── .env.example
│
├── ml_models/                         # Persisted model artifacts (optional; or store in backend)
│   ├── random_forest/
│   ├── lstm/
│   └── isolation_forest/
│
├── data/                              # Local uploads (or use object storage)
│   └── uploads/
│
├── docs/
│   ├── SRS_SmartRiver.md
│   ├── ARCHITECTURE.md
│   ├── DATA_PIPELINE.md
│   ├── DATABASE_SCHEMA.md              # This doc + link to .sql
│   ├── API_SPECIFICATION.md
│   ├── FOLDER_STRUCTURE.md             # This file
│   ├── ML_WORKFLOW.md
│   ├── UI_PAGES.md
│   └── database_schema.sql
│
├── docker-compose.yml                 # Optional: PostgreSQL + backend + frontend
└── README.md
```

## Notes

- **Backend:** One package `app` with subpackages per domain (auth, data, preprocessing, ml, viz, alerts, reports). Models and DB live under `app/models` and `app/db`.
- **Frontend:** Feature-based under `src` — `api`, `components`, `pages`, `context`, `hooks`. Charts and map are reusable under `components/charts` and `components/map`.
- **ML artifacts:** Can live in `backend/app/ml/models/` or a shared `ml_models/` directory; ensure path is configurable via `config`.
- **Data:** CSV uploads can be stored under `data/uploads/` or an S3 bucket; `file_path` in DB points to that location.
