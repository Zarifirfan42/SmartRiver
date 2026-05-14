# SmartRiver — API Specification

Base URL: `/api/v1` (e.g. `https://api.smartriver.local/api/v1`).  
All authenticated endpoints require header: `Authorization: Bearer <access_token>`.

---

## 1. Authentication

### 1.1 Register

- **POST** `/auth/register`  
- **Body:**  
  `{ "email": "string", "password": "string", "full_name": "string?", "role": "public" }`  
- **Response:** `201` + `{ "id", "email", "full_name", "role" }` (no password).  
- **Errors:** `400` validation, `409` email exists.

### 1.2 Login

- **POST** `/auth/login`  
- **Body:** `{ "email": "string", "password": "string" }`  
- **Response:** `200` + `{ "access_token": "string", "token_type": "bearer", "expires_in": number, "user": { "id", "email", "full_name", "role" } }`  
- **Errors:** `401` invalid credentials.

### 1.3 Get current user

- **GET** `/auth/me`  
- **Auth:** Required.  
- **Response:** `200` + user object.

### 1.4 Refresh token (optional)

- **POST** `/auth/refresh`  
- **Body:** `{ "refresh_token": "string" }` or send refresh token in header.  
- **Response:** New access token.

---

## 2. Data Management (Admin)

### 2.1 Upload dataset

- **POST** `/datasets/upload`  
- **Auth:** Required, role = Admin.  
- **Body:** `multipart/form-data` with file field (e.g. `file`) and optional `name`, `description`.  
- **Response:** `201` + `{ "id", "name", "file_path", "file_size_bytes", "row_count", "created_at" }`.  
- **Errors:** `400` invalid file, `413` too large.

### 2.2 List datasets

- **GET** `/datasets`  
- **Auth:** Required.  
- **Query:** `skip`, `limit`, `search` (optional).  
- **Response:** `200` + `{ "items": [...], "total": number }`.

### 2.3 Get dataset

- **GET** `/datasets/{dataset_id}`  
- **Auth:** Required.  
- **Response:** `200` + dataset object.  
- **Errors:** `404`.

### 2.4 Update dataset (metadata)

- **PATCH** `/datasets/{dataset_id}`  
- **Auth:** Required, Admin.  
- **Body:** `{ "name": "string?", "description": "string?" }`.  
- **Response:** `200` + dataset object.

### 2.5 Delete dataset

- **DELETE** `/datasets/{dataset_id}`  
- **Auth:** Required, Admin.  
- **Response:** `204`.  
- **Errors:** `404`.

### 2.6 List prediction logs

- **GET** `/datasets/{dataset_id}/prediction-logs`  
- **Auth:** Required.  
- **Query:** `type` (classification | forecast | anomaly), `skip`, `limit`.  
- **Response:** `200` + `{ "items": [...], "total": number }`.

---

## 3. Preprocessing

### 3.1 Run preprocessing

- **POST** `/preprocessing/run`  
- **Auth:** Required, Admin.  
- **Body:** `{ "dataset_id": number, "options": { "missing_strategy": "drop"|"impute", "remove_duplicates": true, "normalize": true } }`.  
- **Response:** `200` + `{ "dataset_id", "rows_processed", "rows_output", "wqi_computed", "message" }`.  
- **Errors:** `400` invalid dataset/options, `404` dataset not found.

### 3.2 Get preprocessing result summary

- **GET** `/preprocessing/datasets/{dataset_id}/summary`  
- **Auth:** Required.  
- **Response:** `200` + summary (row counts, date range, stations).

---

## 4. Machine Learning

### 4.1 Train classification (Random Forest)

- **POST** `/ml/classification/train`  
- **Auth:** Required, Admin.  
- **Body:** `{ "dataset_id": number }`.  
- **Response:** `200` + `{ "model_version", "metrics": { "accuracy", "f1", "confusion_matrix" }, "message" }`.  
- **Errors:** `400` insufficient data.

### 4.2 Run classification (predict)

- **POST** `/ml/classification/predict`  
- **Auth:** Required, Admin.  
- **Body:** `{ "dataset_id": number }`.  
- **Response:** `200` + `{ "prediction_log_id", "predictions": [ { "station_code", "date", "status" } ] }`.

### 4.3 Train forecasting (LSTM)

- **POST** `/ml/forecasting/train`  
- **Auth:** Required, Admin.  
- **Body:** `{ "dataset_id": number, "horizon_days": 30, "station_code": "string?" }`.  
- **Response:** `200` + `{ "model_version", "metrics": { "mse", "mae" }, "message" }`.

### 4.4 Get forecast

- **POST** `/ml/forecasting/predict`  
- **Auth:** Required.  
- **Body:** `{ "dataset_id": number, "station_code": "string?", "horizon_days": 7|30 }`.  
- **Response:** `200` + `{ "prediction_log_id", "forecast": [ { "date", "wqi" } ] }`.

### 4.5 Run anomaly detection (Isolation Forest)

- **POST** `/ml/anomaly/detect`  
- **Auth:** Required, Admin.  
- **Body:** `{ "dataset_id": number }`.  
- **Response:** `200` + `{ "prediction_log_id", "anomalies": [ { "station_code", "date", "score" } ], "alerts_created": number }`.

---

## 5. Visualization & Dashboard

### 5.1 Dashboard summary

- **GET** `/dashboard/summary`  
- **Auth:** Required.  
- **Query:** `dataset_id` (optional; latest if omitted).  
- **Response:** `200` + `{ "total_stations", "date_range", "latest_wqi_avg", "clean_count", "slightly_polluted_count", "polluted_count", "recent_anomalies_count" }`.

### 5.2 River health (status by station/date)

- **GET** `/dashboard/river-health`  
- **Auth:** Required.  
- **Query:** `dataset_id`, `station_code`, `from_date`, `to_date`.  
- **Response:** `200` + `{ "items": [ { "station_code", "reading_date", "wqi", "river_status" } ] }`.

### 5.3 Time-series data

- **GET** `/dashboard/time-series`  
- **Auth:** Required.  
- **Query:** `dataset_id`, `station_code`, `from_date`, `to_date`, `parameter` (wqi | do | bod | ...).  
- **Response:** `200` + `{ "series": [ { "date", "value" } ] }`.

### 5.4 Forecast data

- **GET** `/dashboard/forecast`  
- **Auth:** Required.  
- **Query:** `dataset_id`, `station_code`, `horizon_days`.  
- **Response:** `200` + `{ "forecast": [ { "date", "wqi" } ], "prediction_log_id" }`.

### 5.5 Map data (stations with latest status)

- **GET** `/dashboard/map`  
- **Auth:** Required.  
- **Query:** `dataset_id`.  
- **Response:** `200` + `{ "stations": [ { "station_code", "name", "lat", "lng", "latest_wqi", "river_status", "last_reading_date" } ] }`.

---

## 6. Alerts

### 6.1 List alerts

- **GET** `/alerts`  
- **Auth:** Required.  
- **Query:** `unread_only`, `skip`, `limit`.  
- **Response:** `200` + `{ "items": [...], "total": number }`.

### 6.2 Mark alert read

- **PATCH** `/alerts/{alert_id}/read`  
- **Auth:** Required.  
- **Body:** `{ "is_read": true }`.  
- **Response:** `200` + alert object.

---

## 7. Export Report

### 7.1 Export report

- **POST** `/reports/export`  
- **Auth:** Required.  
- **Body:** `{ "dataset_id": number?, "format": "csv"|"pdf", "from_date", "to_date", "station_code?" }`.  
- **Response:**  
  - CSV: `200` + file download (Content-Disposition).  
  - PDF: `200` + file download or `202` + job id for async generation.  
- **Errors:** `400` invalid params.

---

## 8. Common Response Shapes

- **Error:** `{ "detail": "string" }` or `{ "detail": [ { "loc": [], "msg": "", "type": "" } ] }` (validation).  
- **Pagination:** `{ "items": [], "total": number }` with query `skip`, `limit`.

---

*Use this specification to implement FastAPI routers and React API client.*
