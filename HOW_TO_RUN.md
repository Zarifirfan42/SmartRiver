# How to Run SmartRiver

Setup and run the **backend** (API), **frontend** (web UI), and optional **ML training**. Paths below use a placeholder; if your folder has spaces (e.g. `FYP 2526`), keep the quotes.

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| **Python 3.10+** | Backend, ML training |
| **Node.js v18+** and **npm** | Frontend |
| **PostgreSQL** (optional) | Only if you connect the app to Postgres later |

**Recommended:** create a Python virtual environment once at the project root so installs do not touch system Python.

**Windows (PowerShell)**

```powershell
cd "C:\path\to\SmartRiver"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
cd /path/to/SmartRiver
python3 -m venv .venv
source .venv/bin/activate
```

---

## 1. Backend — setup and run

The API must run from the **project root** with `PYTHONPATH` set to the repo root.

### Install dependencies

```powershell
cd "C:\path\to\SmartRiver"
.\.venv\Scripts\Activate.ps1
pip install -r requirements-backend-minimal.txt
```

### Run the server

```powershell
cd "C:\path\to\SmartRiver"
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Windows (cmd)**

```cmd
cd "C:\path\to\SmartRiver"
set PYTHONPATH=%CD%
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Linux / macOS**

```bash
cd /path/to/SmartRiver
export PYTHONPATH=.
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Backend URLs

| Item | URL |
|------|-----|
| API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |

### Data

- Put `River Monitoring Dataset.xlsx` or a `.csv` in `datasets/` if you want your own file; otherwise the app may use bundled or sample data on startup.
- Start the **backend before the frontend** in dev so login and API calls work (the Vite dev server proxies `/api` to port 8000 by default).

---

## 2. Frontend — setup and run

```powershell
cd "C:\path\to\SmartRiver\frontend"
npm install
npm run dev
```

- App: **http://localhost:3000**
- Default admin (for uploads / admin pages):
  - **Email:** `admin@smartriver.com`
  - **Password:** `admin123`

---

## 3. Run backend and frontend together (typical development)

1. **Terminal 1 — Backend** (project root, venv activated)

   ```powershell
   cd "C:\path\to\SmartRiver"
   .\.venv\Scripts\Activate.ps1
   $env:PYTHONPATH = (Get-Location).Path
   python -m uvicorn backend.app.main:app --reload --port 8000
   ```

2. **Terminal 2 — Frontend**

   ```powershell
   cd "C:\path\to\SmartRiver\frontend"
   npm run dev
   ```

3. Open **http://localhost:3000**.

---

## 4. ML training — test / train models

Train **Random Forest** (river status), **LSTM** (WQI forecast, needs TensorFlow), and **Isolation Forest** (anomaly), and write metrics to `ml_models/training_metrics.json`.

### Install ML dependencies

From **project root** (venv recommended):

```powershell
cd "C:\path\to\SmartRiver"
.\.venv\Scripts\Activate.ps1
pip install -r requirements-ml.txt
```

### Recommended: full training + metrics JSON

Uses CSVs under `datasets/` (prefers `datasets/by_river/**/*.csv` when present; otherwise the first `.csv` in `datasets/`).

```powershell
cd "C:\path\to\SmartRiver"
$env:PYTHONPATH = (Get-Location).Path
python -m ml_engine.train
```

**Useful options**

| Flag | Meaning |
|------|---------|
| `--csv "FileName"` | Train on `datasets/FileName.csv` (extension optional) |
| `--no-by-river` | Do not merge `by_river` CSVs; use a single root CSV only |
| `--lstm-station "S01"` | Train LSTM on one `station_code` |
| `--lstm-epochs 30` | Fewer epochs for a quicker test run |
| `--no-normalize` | Disable MinMax scaling in preprocessing for the engineered frame |

**Outputs**

| Output | Location |
|--------|----------|
| Random Forest | `ml_models/random_forest/model.joblib` |
| LSTM | `ml_models/lstm/model.keras` and `ml_models/lstm/scaler.joblib` |
| Isolation Forest | `ml_models/anomaly_detection/model.joblib` |
| Metrics (CV, confusion matrix, LSTM vs baseline, etc.) | `ml_models/training_metrics.json` |

The console prints a summary, including **Random Forest feature list** (raw parameters only: `DO`, `BOD`, `COD`, `AN`, `TSS`, `pH`) and **group-aware cross-validation** accuracy. If you have fewer unique stations/rivers than requested folds, **k** is capped (e.g. **k = 3** with three groups) so no empty CV folds occur.

### Alternative: sample pipeline (generates a sample CSV if none given)

```powershell
cd "C:\path\to\SmartRiver"
$env:PYTHONPATH = (Get-Location).Path
python -m ml_engine.run_pipeline
```

- Without TensorFlow: `python -m ml_engine.run_pipeline --no-lstm`

More detail: **docs/ML_PIPELINE_README.md** (if present).

---

## 5. Optional: Database (PostgreSQL)

1. Create a database (e.g. `smartriver`).
2. Run: `psql -U your_user -d smartriver -f docs/database_schema.sql`
3. Copy `backend/.env.example` to `backend/.env` and set `DATABASE_URL=postgresql://user:password@localhost:5432/smartriver`
4. Wire DB usage in `backend/app/main.py` when you enable it.

---

## Summary

| What | Where to run | URL / output |
|------|----------------|--------------|
| Frontend | `frontend/` → `npm run dev` | http://localhost:3000 |
| Backend | project root → `python -m uvicorn backend.app.main:app --reload --port 8000` | http://localhost:8000 |
| API docs | (backend running) | http://localhost:8000/docs |
| ML train | project root → `python -m ml_engine.train` | `ml_models/`, `training_metrics.json` |

---

## Troubleshooting

### Backend: "No module named uvicorn"

Use a venv and `pip install -r requirements-backend-minimal.txt`, then run `python -m uvicorn ...` from the project root with `PYTHONPATH` set.

### Frontend: "Network error" or blank data

Start the backend on port **8000** first. Hard refresh: Ctrl+Shift+R.

### ML: "TensorFlow not installed" or LSTM skipped

Run `pip install -r requirements-ml.txt`. On Windows, recent TensorFlow may be CPU-only; GPU on native Windows is limited for TF ≥ 2.11 (WSL2 is an option for GPU).

### ML: TensorFlow / oneDNN warnings

Informational. To reduce oneDNN messages: `$env:TF_ENABLE_ONEDNN_OPTS = "0"` (PowerShell) before training.

### Backend: "WARNING: Ignoring invalid distribution ~rotobuf"

A broken protobuf folder under `site-packages`; you can remove or rename the `~rotobuf` folder. Often harmless.
