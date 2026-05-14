# SmartRiver — Database Schema (Overview)

This document summarizes the database design. The executable SQL is in **`database_schema.sql`**.

## 1. Entity-Relationship Overview

- **users** — Accounts (Admin / Public); used for auth and audit (uploaded_by, triggered_by).
- **datasets** — Metadata for uploaded CSV files (path, size, row count, uploader).
- **river_stations** — Optional master list of stations (code, name, lat/lng, river, state).
- **water_quality_readings** — Raw readings from CSV (per dataset, station, date; DOE parameters + optional WQI).
- **processed_readings** — Preprocessed data with WQI, river_status, and optional features (for ML and dashboard).
- **prediction_logs** — All ML outputs (classification, forecast, anomaly) with result payload in JSONB.
- **alerts** — Early warning records linked to anomaly prediction logs; can be marked read.

## 2. Table Summary

| Table | Purpose |
|-------|--------|
| users | Authentication and RBAC |
| datasets | Uploaded CSV metadata |
| river_stations | Station master (optional) |
| water_quality_readings | Raw data from CSV |
| processed_readings | Cleaned data + WQI + features |
| prediction_logs | Classification, forecast, anomaly results |
| alerts | Anomaly alerts for dashboard/notifications |

## 3. Key Relationships

- `datasets.uploaded_by` → `users.id`
- `water_quality_readings.dataset_id` → `datasets.id`
- `water_quality_readings.station_id` → `river_stations.id` (optional)
- `processed_readings.dataset_id` → `datasets.id`
- `prediction_logs.dataset_id` → `datasets.id`, `prediction_logs.triggered_by` → `users.id`
- `alerts.prediction_log_id` → `prediction_logs.id`

## 4. Enums

- **user_role:** `admin`, `public`
- **river_status:** `clean`, `slightly_polluted`, `polluted`
- **prediction_type:** `classification`, `forecast`, `anomaly`

## 5. Indexes

Indexes are defined in `database_schema.sql` for:

- User lookup (email, role)
- Dataset lookup (uploaded_by, created_at)
- Readings by dataset, station, date
- Prediction logs by type, dataset, station, date, created_at
- Alerts by created_at and unread

Run `database_schema.sql` against PostgreSQL to create the schema.
