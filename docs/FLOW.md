# SmartRiver — End-to-end flow

## Flow

```
Dataset → Data Preprocessing → ML Engine → Prediction API → Visualization Dashboard
```

## 1. Dataset

- **Upload:** `POST /api/v1/datasets/upload` (CSV file).
- Backend saves file under `datasets/uploads/` and registers in repository (in-memory DB).
- Response: `dataset_id`, use for preprocessing or send same file to preprocessing.

## 2. Data preprocessing

- **Run:** `POST /api/v1/preprocessing/run` with either:
  - `file`: CSV (multipart), or
  - `dataset_id`: existing dataset ID.
- Pipeline: load CSV → clean → impute missing → compute WQI → save readings to repository.
- Stored readings power dashboard **summary** and **time-series** (WQI trend chart).

## 3. ML engine

- **Train:** `POST /api/v1/ml/train` with CSV file.
  - Preprocesses data, trains Random Forest and Isolation Forest (LSTM if TensorFlow installed).
  - Saves models under `ml_models/random_forest`, `ml_models/anomaly_detection`, `ml_models/lstm`.
  - Writes training metrics to repository (prediction_logs).
- **Predict:**
  - `POST /api/v1/ml/predict/classification` — CSV → river status per row → stored in prediction_logs.
  - `POST /api/v1/ml/predict/forecast` — optional CSV with WQI, or uses latest readings → forecast list → stored.
  - `POST /api/v1/ml/predict/anomaly` — CSV → anomalies + alerts created in repository.

## 4. Prediction API (storage)

- All prediction results are saved via `backend/db/repository.py`:
  - `prediction_logs`: type = classification | forecast | anomaly, `result_json` = payload.
  - `alerts`: created when anomaly is detected; listed on dashboard and Alerts page.

## 5. Visualization dashboard

- **Dashboard** (React) calls:
  - `GET /api/v1/dashboard/summary` → summary cards, WQI gauge, status breakdown.
  - `GET /api/v1/dashboard/time-series` → WQI trend chart.
  - `GET /api/v1/dashboard/forecast` → forecast chart.
  - `GET /api/v1/alerts/` → anomaly alerts panel.
- Data comes from repository (filled by preprocessing and ML predict).

## Quick test

1. Start backend: from project root, `uvicorn backend.app.main:app --reload --port 8000`.
2. Start frontend: `cd frontend && npm run dev`.
3. Upload a CSV: `POST /api/v1/datasets/upload` or use Upload page (admin).
4. Run preprocessing: `POST /api/v1/preprocessing/run` with the same CSV (or `dataset_id`).
5. Open dashboard: WQI trend and summary should show.
6. (Optional) Train: `POST /api/v1/ml/train` with CSV; then run predict endpoints and see alerts/forecast on dashboard.

## API base URL

- Frontend expects backend at `http://localhost:8000` (or set `VITE_API_URL`).
