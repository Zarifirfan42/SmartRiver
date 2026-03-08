# SmartRiver — Data Pipeline

## 1. End-to-End Data Flow

```
[User Upload CSV] → [Validate & Store] → [Preprocessing] → [WQI + Features]
                                                                    │
        ┌───────────────────────────────────────────────────────────┼───────────────────────────────────────┐
        ▼                                                           ▼                                       ▼
[Classification RF]                                          [Forecasting LSTM]                    [Anomaly IsoForest]
        │                                                           │                                       │
        ▼                                                           ▼                                       ▼
[Prediction Log]                                            [Prediction Log]                        [Prediction Log]
        │                                                           │                                       │
        └───────────────────────────────────────────────────────────┼───────────────────────────────────────┘
                                                                    ▼
                                                    [Dashboard / Alerts / Export]
```

## 2. Pipeline Stages

### 2.1 Ingestion (Data Management)

1. Admin uploads CSV (DOE format).  
2. Backend validates extension and basic structure (required columns).  
3. File saved to disk; metadata (filename, size, uploader_id, created_at) stored in DB.  
4. Optional: parse and store raw rows in `water_quality_readings` for queryability.

### 2.2 Preprocessing

1. **Load:** Read CSV into pandas DataFrame.  
2. **Missing values:** Configurable strategy — drop rows/columns or impute (mean/median/mode).  
3. **Duplicates:** Drop duplicate rows (optionally by key columns e.g. station + datetime).  
4. **Normalization:** Apply Min-Max or StandardScaler to selected numeric columns (for ML).  
5. **WQI calculation:** Compute WQI from DOE sub-indices (DO, BOD, COD, NH3-N, TSS, pH).  
6. **Feature engineering:**  
   - Rolling mean/std for key parameters (e.g., 7-day window).  
   - Lag features for WQI (e.g., 1, 7, 14 days).  
   - Date features (month, day of year) if useful for seasonality.  
7. Output: cleaned DataFrame and/or persisted table `processed_readings` (or equivalent).

### 2.3 ML Pipeline

- **Input:** Preprocessed data (with WQI and features).  
- **Classification:**  
  - Train Random Forest on labels: Clean / Slightly Polluted / Polluted (from WQI bands or existing labels).  
  - Predict per station/date; save to `prediction_log` with type = `classification`.  
- **Forecasting:**  
  - Build sequences from WQI time series; train LSTM to predict next 7–30 days.  
  - Save forecast series to `prediction_log` with type = `forecast`.  
- **Anomaly:**  
  - Fit Isolation Forest on WQI (and optionally other parameters).  
  - Flag anomalies; save to `prediction_log` with type = `anomaly` and trigger alert.

### 2.4 Serving & Visualization

- Dashboard and map read from:  
  - `water_quality_readings` / `processed_readings`  
  - `prediction_log` (filtered by type and date range)  
- Alerts: query `prediction_log` where type = `anomaly` and shown in Alerts panel; optional email/push later.  
- Export: same data sources, filtered by user selection, generated as CSV/PDF.

## 3. Data Dependencies

- Preprocessing **depends on** raw dataset (upload).  
- Classification and Anomaly **depend on** preprocessed data (with WQI).  
- Forecasting **depends on** preprocessed time series (WQI per station/date).  
- Dashboard/Alerts/Export **depend on** stored readings and prediction logs.

---

*See ML_WORKFLOW.md for detailed ML steps and WQI formula.*
