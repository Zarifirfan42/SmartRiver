# How to Run SmartRiver

Quick steps to run the **frontend** (web UI) and **backend** (API). Optional: database and ML pipeline.

---

## Prerequisites

- **Node.js** (v18+) and **npm** — for the frontend  
- **Python 3.10+** — for the backend  
- **PostgreSQL** (optional) — only if you enable the database later  

---

## 1. Run the frontend (web interface)

Open a terminal and run (use **quotes** around the path if it contains spaces, e.g. `FYP 2526`):

```powershell
cd "c:\Users\irfan\Downloads\FYP 2526\SmartRiver\frontend"
npm install
npm run dev
```

- The app will be at **http://localhost:3000**
- **Login** with the default admin account to access Dataset Upload and admin features:
  - **Email:** `admin@smartriver.com`
  - **Password:** `admin123`
- Or **Register** a new account (role: User). Only admins can upload datasets, manage stations, and trigger processing.

---

## 2. Run the backend (API)

Run the backend **from the project root**. Use **quotes** around paths that contain spaces. Use `python -m uvicorn` so uvicorn is found even if it’s not on your PATH.

**Windows (PowerShell)** — use quoted path and `python -m uvicorn`:

```powershell
cd "c:\Users\irfan\Downloads\FYP 2526\SmartRiver"
$env:PYTHONPATH = (Get-Location).Path
pip install -r requirements-backend-minimal.txt
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Windows (Command Prompt)**

```cmd
cd "c:\Users\irfan\Downloads\FYP 2526\SmartRiver"
set PYTHONPATH=%CD%
pip install -r requirements-backend-minimal.txt
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Linux / macOS**

```bash
cd "/path/to/SmartRiver"
export PYTHONPATH=.
pip install -r requirements-backend-minimal.txt
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

- API will be at **http://localhost:8000**
- API docs (Swagger): **http://localhost:8000/docs**
- Frontend uses `http://localhost:8000` for API (or set `VITE_API_URL`).

---

## 3. Run both together (typical development)

1. **Terminal 1 — Backend** (use a venv and quoted path; run from project root)

   ```powershell
   cd "c:\Users\irfan\Downloads\FYP 2526\SmartRiver"
   .\.venv\Scripts\Activate.ps1
   $env:PYTHONPATH = (Get-Location).Path
   python -m uvicorn backend.app.main:app --reload --port 8000
   ```

2. **Terminal 2 — Frontend** (use quoted path)

   ```powershell
   cd "c:\Users\irfan\Downloads\FYP 2526\SmartRiver\frontend"
   npm install
   npm run dev
   ```

3. Open **http://localhost:3000** in your browser.

---

## 4. Optional: ML pipeline (train models)

From the **project root**:

```powershell
cd "c:\Users\irfan\Downloads\FYP 2526\SmartRiver"
$env:PYTHONPATH = (Get-Location).Path
pip install -r requirements-ml.txt
python -m ml_engine.run_pipeline --no-lstm
```

- `--no-lstm` skips the LSTM model if TensorFlow is not installed.
- With TensorFlow: run without `--no-lstm` to train all three models (RF, LSTM, Isolation Forest).
- This creates sample data under `datasets/` and saves models under `ml_models/`.

See **docs/ML_PIPELINE_README.md** for full ML usage.

---

## 5. Optional: Database (PostgreSQL)

If you later connect the backend to a database:

1. Create a database (e.g. `smartriver`).
2. Run the schema:  
   `psql -U your_user -d smartriver -f docs/database_schema.sql`
3. Copy `backend/.env.example` to `backend/.env` and set:

   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/smartriver
   ```

4. Uncomment the database and router code in `backend/app/main.py` when you implement it.

---

## Summary

| What              | Command (from project root) | URL                  |
|-------------------|-----------------------------|----------------------|
| Frontend          | `cd frontend && npm run dev` | http://localhost:3000 |
| Backend           | From project root: `$env:PYTHONPATH=. ; python -m uvicorn backend.app.main:app --reload --port 8000` | http://localhost:8000 |
| API docs          | (backend running)           | http://localhost:8000/docs |
| ML pipeline       | `python -m ml_engine.run_pipeline --no-lstm` | — |

For the UI, you only need to run **frontend** and **backend** (backend can run with the current stub endpoints).

---

## Troubleshooting

### Backend: "No module named uvicorn" or pip error on dotenv.exe

- **Cause:** `pip install -r requirements.txt` failed (e.g. OSError when writing to `Python312\Scripts`), so uvicorn was never installed.
- **Fix:** Use a **virtual environment** and the **minimal** requirements:
  1. `cd "c:\Users\irfan\Downloads\FYP 2526\SmartRiver"`
  2. `python -m venv .venv`
  3. `.\.venv\Scripts\Activate.ps1`
  4. `pip install -r requirements-backend-minimal.txt`
  5. `$env:PYTHONPATH = (Get-Location).Path`
  6. `python -m uvicorn backend.app.main:app --reload --port 8000`

### Backend: "WARNING: Ignoring invalid distribution ~rotobuf"

- A previous protobuf install left a broken folder. You can rename or remove the folder `~rotobuf` under your Python `site-packages`. Optional; the app can still run.

### Frontend: blank white page

- Open **Developer Tools** (F12) → **Console** tab and check for red errors.
- Ensure the **backend** is running at **http://localhost:8000**.
- Hard refresh: Ctrl+Shift+R.
