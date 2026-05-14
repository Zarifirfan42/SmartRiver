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

## 4. Machine learning — train models and read results

This is the path to **produce** RF / LSTM / Isolation Forest artifacts and a **metrics JSON** the dashboard and API can rely on after you copy or symlink artifacts into place.

### 4.1 Install ML dependencies

From **project root** (same venv as the backend is fine):

```powershell
cd "C:\path\to\SmartRiver"
.\.venv\Scripts\Activate.ps1
pip install -r requirements-ml.txt
```

- **TensorFlow** is required for the **LSTM**; without it, training skips the LSTM step.
- **matplotlib** is used to save the LSTM **training vs validation loss** plot (`lstm_training_loss.png`). If it is missing, training still completes; the plot path in metrics may be empty.

### 4.2 Run training (main command)

Always run from the **project root** with **`PYTHONPATH` = repo root** so imports resolve.

**Windows (PowerShell)**

```powershell
cd "C:\path\to\SmartRiver"
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
python -m ml_engine.train
```

**Linux / macOS**

```bash
cd /path/to/SmartRiver
source .venv/bin/activate
export PYTHONPATH=.
python -m ml_engine.train
```

**Data:** By default, training loads **`datasets/by_river/**/*.csv`** when that folder exists; otherwise it uses the first `*.csv` under `datasets/`. Put DOE-style river CSVs there (with `date`, parameters, and `WQI` after preprocessing).

### 4.3 CLI options (useful flags)

| Flag | Meaning |
|------|---------|
| `--csv "FileName"` | Train on `datasets/FileName.csv` only (extension optional) |
| `--no-by-river` | Do not merge `by_river` CSVs; single root CSV only |
| `--year-from Y` / `--year-to Y` | Keep rows whose `date` falls in that calendar year range |
| `--lstm-station "S01"` | Train the LSTM on one `station_code` |
| `--lstm-seq-len 30` | LSTM input window length (days) |
| `--lstm-horizon 7` | Multi-step forecast length |
| `--lstm-epochs 30` | Fewer epochs for a quicker test run |
| `--no-normalize` | Disable MinMax scaling in the engineered preprocessing frame |
| `--metrics-json path.json` | Write metrics somewhere other than `ml_models/training_metrics.json` |

Example: train on one CSV for 2023–2025, quick LSTM:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m ml_engine.train --csv "your_file" --year-from 2023 --year-to 2025 --lstm-epochs 30
```

### 4.4 Where your ML results go

| Output | Location | What it is |
|--------|----------|----------------|
| **Metrics report** | `ml_models/training_metrics.json` | RF accuracy / F1 / confusion matrix; LSTM RMSE, MAE, R², baseline comparison, `loss_plot_path`; isolation forest counts |
| **Random Forest** | `ml_models/random_forest/model.joblib` | River status classifier |
| **LSTM (forecast)** | `ml_models/lstm/lstm_model.keras` | Keras model (multivariate input: WQI, lags, monsoon features) |
| **LSTM scalers + config** | `ml_models/lstm/scaler.joblib` | `scaler_X`, `scaler_y`, and `config` (`seq_len`, `horizon`, `feature_columns`, …) for inference |
| **LSTM loss curve** | `ml_models/lstm/lstm_training_loss.png` | Training vs validation loss (Huber) when matplotlib is installed |
| **Isolation Forest** | `ml_models/anomaly_detection/model.joblib` | Anomaly detector |

The terminal prints a short summary (including RF features and CV notes). Open **`training_metrics.json`** for full numbers; open **`lstm_training_loss.png`** to check overfitting.

### 4.5 Using results with the FastAPI backend

After training, the backend expects artifacts under **`ml_models/`** (same layout as above). Restart the API if it was already running, then use forecast routes (e.g. `/predict/forecast` or `/forecast`) so the app loads **`lstm_model.keras`** and **`scaler.joblib`**. Forecast inputs need **dated rows** (or the API may synthesize dates for CSV uploads) so the LSTM can build lag and monsoon features.

### 4.6 Optional: LSTM R² diagnostics

From project root (TensorFlow required for full run; partial stats without it):

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m ml_engine.diagnose_lstm_r2 --csv sample_water_quality --no-by-river
```

Add `--plot path.png` to set the actual-vs-predicted scatter output path.

### 4.7 Alternative: sample pipeline

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
| ML train | project root → `python -m ml_engine.train` | `ml_models/` (e.g. `lstm_model.keras`, `training_metrics.json`, `lstm_training_loss.png`) |

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
