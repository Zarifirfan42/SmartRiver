# SmartRiver

**SmartRiver** is an AI-based River Water Quality Monitoring System built with **React + TailwindCSS** (frontend) and **FastAPI + Python** (backend). It monitors river water quality using **Water Quality Index (WQI)** and supports:

- **Classification** (Random Forest)
- **Forecasting** (LSTM)
- **Anomaly detection** (Isolation Forest)

Data is based on **DOE Malaysia** river water quality datasets.

---

## Tech stack

- **Frontend**: React, TailwindCSS, Vite
- **Backend**: FastAPI, Python
- **ML**: scikit-learn (Random Forest, Isolation Forest), TensorFlow/Keras (LSTM)
- **Storage**:
  - Runtime datasets: `datasets/`
  - Saved models: `ml_models/`
  - Auth + feedback persistence: SQLite (default)
  - Optional full schema: PostgreSQL (`database/schema.sql`)

---

## Folder structure

| Path | Purpose |
|------|---------|
| `frontend/` | React + TailwindCSS web app |
| `backend/` | FastAPI app, controllers, services, auth |
| `modules/` | Shared domain logic (data management, preprocessing, ML, visualization/alerts) |
| `ml_engine/` | ML pipeline/services (training + inference helpers) |
| `ml_models/` | Saved ML model artifacts (joblib / keras) |
| `datasets/` | Uploaded datasets + sample dataset (`datasets/uploads/` for uploads) |
| `database/` | SQL schemas (PostgreSQL reference) |
| `docs/` | Documentation |

---

## Quick start

### Prerequisites

- **Node.js** 18+ (frontend)
- **Python** 3.10+ (backend + ML)

### 1) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

### 2) Backend

Run from project root so imports work.

```powershell
cd SmartRiver
$env:PYTHONPATH = (Get-Location).Path
cd backend
pip install -r ../requirements.txt
uvicorn app.main:app --reload --port 8000
```

API base: `http://localhost:8000/api/v1`  
Swagger: `http://localhost:8000/docs`

### 3) Dataset

- Put your DOE Malaysia dataset (CSV/Excel) inside `datasets/`
- Uploads (admin UI) are stored under `datasets/uploads/`

---

## Training models

The training script is at `ml_engine/train.py` and saves:

- Random Forest → `ml_models/random_forest/model.joblib`
- LSTM → `ml_models/lstm/model.keras`
- Isolation Forest → `ml_models/anomaly_detection/model.joblib`

---

## Environment variables

Copy `.env.example` to `.env` and fill in values as needed.

