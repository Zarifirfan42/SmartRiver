# SmartRiver ML Pipeline

End-to-end pipeline: **data ingestion → cleaning → imputation → WQI → feature engineering → train RF / LSTM / Isolation Forest** with evaluation metrics and prediction API.

## 1. Pipeline stages

| Stage | Module | Description |
|-------|--------|-------------|
| **Data ingestion** | `data_preprocessing.services.pipeline.ingest_csv` | Load CSV, normalize column names (DO, BOD, COD, AN, TSS, pH), parse date/station |
| **Data cleaning** | `clean_data` | Drop duplicates, coerce numerics, drop rows with all params null |
| **Missing value imputation** | `impute_missing` | SimpleImputer: mean/median or drop |
| **WQI calculation** | `data_preprocessing.utils.wqi_calculator` | DOE Malaysia sub-indices + weighted WQI; map to clean / slightly_polluted / polluted |
| **Feature engineering** | `feature_engineering` | Rolling mean/std of WQI, lag features (1, 7, 14 days), optional MinMax normalization |

## 2. Models

### Random Forest (classification)
- **Target:** River status (clean / slightly_polluted / polluted).
- **Features:** WQI, DO, BOD, COD, AN, TSS, pH + rolling/lag if present.
- **Evaluation:** Accuracy, F1 (weighted), confusion matrix, classification report.
- **Artifacts:** `ml_models/random_forest/model.joblib`.

### LSTM (forecasting)
- **Target:** WQI next 7–30 days.
- **Input:** Time series of WQI (per station or global); sequences of length `seq_len` (e.g. 30).
- **Evaluation:** RMSE, MAE on hold-out period.
- **Artifacts:** `ml_models/lstm/lstm_model.keras`, `lstm_scaler.joblib`.
- **Requires:** TensorFlow.

### Isolation Forest (anomaly detection)
- **Input:** WQI and DOE parameters per row.
- **Output:** Anomaly flag (-1) and decision score per row.
- **Evaluation:** Count of anomalies (contamination ~0.05).
- **Artifacts:** `ml_models/isolation_forest/model.joblib`.

## 3. Running the pipeline

From **project root** (SmartRiver/):

```bash
# Install ML dependencies
pip install -r requirements-ml.txt

# Optional: with TensorFlow for LSTM
pip install tensorflow

# Run full pipeline (generates sample CSV if none given)
python -m ml_engine.run_pipeline

# With your own CSV and output directory
python -m ml_engine.run_pipeline --csv path/to/doe_data.csv --output-dir ml_models

# Skip LSTM if TensorFlow not installed
python -m ml_engine.run_pipeline --no-lstm
```

## 4. Prediction API

Use `PredictionAPI` to load saved models and run predictions:

```python
from ml_engine.services.prediction_api import get_prediction_api
import pandas as pd

api = get_prediction_api()  # loads from ml_models/

# Classification
df = pd.read_csv("preprocessed.csv")
statuses = api.predict_river_status(df)  # list of {index, river_status}

# Forecast (needs LSTM trained)
forecast = api.predict_wqi_forecast(df, horizon=7, station_code="S01")  # list of 7 WQI values

# Anomaly
anomalies = api.detect_anomalies(df)  # list of {station_code, date, score, is_anomaly}
```

## 5. REST API (FastAPI)

Wire the ML router in your FastAPI app:

```python
from ml_engine.controllers.ml_controller import router as ml_router
app.include_router(ml_router, prefix="/api/v1/ml", tags=["ML"])
```

Endpoints:
- **POST /api/v1/ml/train** — Upload CSV, run full training; returns metrics (Accuracy, RMSE, MAE, anomaly count).
- **POST /api/v1/ml/predict/classification** — Upload CSV; returns predictions per row.
- **POST /api/v1/ml/predict/forecast** — Upload CSV + query params `horizon`, `station_code`; returns forecast list.
- **POST /api/v1/ml/predict/anomaly** — Upload CSV; returns list of anomalies.

## 6. CSV format

Expected columns (after normalization): `date`, `station_code`, `DO`, `BOD`, `COD`, `AN` (NH3-N), `TSS`, `pH`.  
Column name variants (e.g. `do_mg_l`, `nh3_n`) are mapped automatically.

## 7. Evaluation metrics summary

| Model | Metrics |
|-------|---------|
| Random Forest | **Accuracy**, **F1 (weighted)**, confusion matrix |
| LSTM | **RMSE**, **MAE** |
| Isolation Forest | Anomaly count (contamination-based) |
