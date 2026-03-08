# SmartRiver
<<<<<<< HEAD
AI-based River Water Quality Monitoring System
=======

**Predictive River Pollution Monitoring System** — Full-stack AI project for monitoring river water quality using machine learning and a web dashboard. Data source: DOE Malaysia.

- **Backend:** FastAPI + Python  
- **Frontend:** React + TailwindCSS  
- **ML:** Scikit-learn (Random Forest, Isolation Forest), TensorFlow (LSTM)

---

## Project structure and purpose

```
SmartRiver/
│
├── frontend/                    # React + TailwindCSS web app
│   ├── dashboard/               # Dashboard layout and summary widgets (in src/dashboard)
│   ├── components/              # Reusable UI components
│   ├── pages/                   # Page-level screens (in src/pages)
│   └── charts/                  # Chart components: WQI gauge, time-series (in src/charts)
│
├── backend/                     # FastAPI + Python API
│   ├── api/                     # Route registration and API wiring
│   ├── auth/                    # JWT, login, get_current_user, require_admin
│   ├── controllers/             # HTTP handlers (FastAPI routers)
│   └── services/                # Business logic (dataset, ML orchestration)
│
├── modules/                     # Domain modules (shared logic)
│   ├── data_management/        # Auth, RBAC, dataset CRUD, prediction logs
│   ├── data_preprocessing/     # Cleaning, imputation, WQI, feature engineering
│   ├── ml_engine/               # RF classification, LSTM forecast, anomaly detection
│   └── visualization_alert/    # Dashboard data, alerts, report export
│
├── ml_models/                   # Persisted model artifacts
│   ├── random_forest/          # Classification model (joblib)
│   ├── lstm/                    # Forecasting model (Keras)
│   └── anomaly_detection/       # Isolation Forest (joblib)
│
├── database/
│   ├── schema.sql               # PostgreSQL DDL
│   └── migrations/              # Migration scripts
│
├── datasets/                    # Uploaded CSV files (runtime)
│
├── docs/                        # SRS, architecture, API spec, ML workflow
│
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── .gitignore
```

### Folder purposes

| Folder | Purpose |
|--------|---------|
| **frontend/dashboard** | Dashboard layout and summary cards; entry for dashboard-specific UI. |
| **frontend/components** | Shared UI (buttons, cards, layout). |
| **frontend/pages** | Full-page screens (login, dashboard, river health, forecast, alerts, export). |
| **frontend/charts** | Reusable charts (WQI gauge, time-series, forecast). |
| **backend/api** | Central API router and route registration. |
| **backend/auth** | JWT create/decode, `get_current_user`, `require_admin` for protected routes. |
| **backend/controllers** | FastAPI routers; thin layer that calls services. |
| **backend/services** | Business logic (e.g. dataset upload, ML orchestration). |
| **modules/data_management** | User/dataset/prediction-log domain logic. |
| **modules/data_preprocessing** | Data pipeline: clean, impute, WQI, features. |
| **modules/ml_engine** | Train/predict: RF, LSTM, Isolation Forest. |
| **modules/visualization_alert** | Dashboard aggregates, alerts, reports. |
| **ml_models/** | Saved models (RF, LSTM, anomaly) produced by training. |
| **database/** | Schema and migrations for PostgreSQL. |
| **datasets/** | Uploaded CSV storage. |
| **docs/** | Documentation (SRS, architecture, API, ML). |

---

## Quick start

### Prerequisites

- **Node.js** 18+ and **npm** (frontend)  
- **Python** 3.10+ (backend + ML)  
- **PostgreSQL** (optional, for full backend)

### 1. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**.

### 2. Backend

From **project root** (so `backend` and `modules` are on the path):

```bash
# Windows PowerShell
cd SmartRiver
$env:PYTHONPATH = (Get-Location).Path
cd backend
pip install -r ../requirements.txt
uvicorn app.main:app --reload --port 8000
```

API: **http://localhost:8000** — Docs: **http://localhost:8000/docs**

### 3. Database (optional)

```bash
createdb smartriver
psql -U postgres -d smartriver -f database/schema.sql
```

Set `DATABASE_URL` in `backend/.env`.

---

## Push to GitHub

You can’t push to your GitHub from this environment; do it from your machine:

1. **Create a new repo** on [GitHub](https://github.com/Zarifirfan42) (e.g. `SmartRiver`). Don’t add a README or .gitignore in the UI if the project already has them.

2. **From your project folder** (e.g. `SmartRiver`):

```bash
git init
git add .
git commit -m "Initial commit: SmartRiver full-stack structure"
git branch -M main
git remote add origin https://github.com/Zarifirfan42/SmartRiver.git
git push -u origin main
```

3. If the repo already exists and has content:

```bash
git remote add origin https://github.com/Zarifirfan42/SmartRiver.git
git pull origin main --allow-unrelated-histories
git push -u origin main
```

Use **GitHub CLI** (`gh repo create`) or **GitHub Desktop** if you prefer.

---

## License and author

FYP project — Intelligent Computing / Data Science.  
Author: [Zarif Irfan Bin Khairussli](https://github.com/Zarifirfan42).
>>>>>>> 5b4bd9b (Initial SmartRiver project commit)
