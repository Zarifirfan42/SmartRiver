# SmartRiver — ML Workflow

## 1. Water Quality Index (WQI) — DOE Malaysia

Malaysian WQI is computed from six sub-indices (DO, BOD, COD, NH3-N, TSS, pH). Each sub-index is converted to a 0–100 scale using DOE formulas; then WQI is a weighted average.

### 1.1 Sub-index formulas (typical DOE)

- **DO (Dissolved Oxygen, mg/L):** Piecewise linear (e.g. 100 at ≥7, 0 at 0).  
- **BOD (Biochemical Oxygen Demand, mg/L):** Inverse (e.g. 100 at 0, 0 at ≥6).  
- **COD (Chemical Oxygen Demand, mg/L):** Inverse.  
- **NH3-N (Ammoniacal Nitrogen, mg/L):** Inverse.  
- **TSS (Total Suspended Solids, mg/L):** Inverse.  
- **pH:** Optimal around 7; decrease towards extremes.

(Exact coefficients and breakpoints should be taken from official DOE documentation.)

### 1.2 WQI formula

```
WQI = (0.22 * SIDO) + (0.19 * SIBOD) + (0.16 * SICOD) + (0.15 * SIAN) + (0.16 * SITSS) + (0.12 * SIpH)
```

Where `SI*` are the sub-indices (0–100). Then map WQI to river status:

| WQI Range   | River Status        |
|-------------|---------------------|
| 81–100      | Clean               |
| 60–80       | Slightly Polluted   |
| 0–59        | Polluted            |

---

## 2. Classification — Random Forest

### 2.1 Goal

Classify each record (e.g. per station + date) into **Clean**, **Slightly Polluted**, or **Polluted** based on WQI (or existing labels).

### 2.2 Workflow

1. **Input:** `processed_readings` (or DataFrame with WQI and optional features).  
2. **Target:** `river_status` derived from WQI bands (or use existing label column).  
3. **Features:** WQI, sub-indices (DO, BOD, COD, NH3-N, TSS, pH), optional engineered (rolling mean, lags).  
4. **Split:** Time-based or random (e.g. 80% train, 20% test).  
5. **Model:** `sklearn.ensemble.RandomForestClassifier` (n_estimators e.g. 100–200).  
6. **Output:** Trained model saved (joblib/pickle); metrics (accuracy, F1, confusion matrix) returned.  
7. **Predict:** Load model, predict on new preprocessed data; write results to `prediction_logs` with type `classification`.

### 2.3 Hyperparameters (suggested)

- `n_estimators`: 100–200  
- `max_depth`: 10–20  
- `min_samples_leaf`: 5  
- `class_weight`: `balanced` if imbalanced  

---

## 3. Forecasting — LSTM

### 3.1 Goal

Predict WQI for the next **7–30 days** per station (or globally).

### 3.2 Workflow

1. **Input:** Time series of WQI (and optionally other parameters) per station, sorted by date.  
2. **Sequence construction:** Sliding window — e.g. past 30 days → next 7 or 30 days.  
3. **Normalization:** Min-Max or StandardScaler on WQI (fit on train only).  
4. **Model:** Keras/TensorFlow LSTM — e.g. 2 LSTM layers (64–128 units), Dense output (7 or 30 units).  
5. **Train:** Fit on sequences; validate on hold-out period; early stopping.  
6. **Save:** Model (`.h5` or SavedModel) and scaler (joblib).  
7. **Predict:** Load model and scaler; build last window from recent data; predict; inverse transform; save to `prediction_logs` with type `forecast`.

### 3.3 Suggested architecture

```text
Input (seq_len, n_features) → LSTM(128) → Dropout → LSTM(64) → Dropout → Dense(horizon)
Loss: MSE or MAE. Optimizer: Adam.
```

---

## 4. Anomaly Detection — Isolation Forest

### 4.1 Goal

Detect **abnormal pollution spikes** (unusual WQI or parameter values).

### 4.2 Workflow

1. **Input:** Preprocessed data — e.g. WQI and key parameters (DO, BOD, etc.) per station/date.  
2. **Features:** WQI, sub-indices; optional rolling z-score.  
3. **Model:** `sklearn.ensemble.IsolationForest` (contamination e.g. 0.05–0.1).  
4. **Fit:** On historical data (or per station).  
5. **Predict:** `decision_function` or `predict`; flag samples with score &lt; threshold or label = -1.  
6. **Output:** List of (station_code, date, score); insert into `prediction_logs` type `anomaly` and create rows in `alerts` for early warning.

### 4.3 Hyperparameters

- `n_estimators`: 100–200  
- `contamination`: 0.05–0.1  
- `max_samples`: `min(256, n_samples)`  

---

## 5. Execution Order (Pipeline)

1. **Upload CSV** → store raw data.  
2. **Run preprocessing** → WQI + features → `processed_readings`.  
3. **Train classification** (optional) → save RF model.  
4. **Run classification** → write to `prediction_logs`.  
5. **Train LSTM** (optional) → save LSTM + scaler.  
6. **Run forecast** → write to `prediction_logs`.  
7. **Run anomaly detection** → write to `prediction_logs` + `alerts`.  
8. Dashboard and export read from DB (readings + prediction_logs + alerts).

---

## 6. File and Config

- **Model storage:** Configurable path (e.g. `ml_models/` or `backend/app/ml/artifacts/`).  
- **Versions:** Save with dataset_id or timestamp so multiple runs don’t overwrite.  
- **Reproducibility:** Set `random_state` in sklearn and TensorFlow seeds where applicable.

---

*Reference: DOE Malaysia WQI documentation; Scikit-learn and Keras official docs for APIs.*
