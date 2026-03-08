# SmartRiver — System Architecture

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Browser)                                    │
│  React.js + TailwindCSS │ Plotly/Chart.js │ Leaflet                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTPS / REST API
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (Python FastAPI)                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Auth & RBAC  │ │ Data Mgmt    │ │ Preprocess   │ │ ML Engine                │ │
│  │ (JWT, roles) │ │ (CRUD CSV)   │ │ (WQI, etc.)  │ │ RF / LSTM / IsoForest   │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────────────────────┐│
│  │ Visualization & Alert API (dashboard data, forecasts, anomalies, reports)     ││
│  └──────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │ PostgreSQL   │    │ File Store   │    │ Redis (opt.) │
            │ (users,      │    │ (uploaded    │    │ cache/session│
            │  datasets,   │    │  CSV, models)│    │              │
            │  logs, etc.) │    │              │    └──────────────┘
            └──────────────┘    └──────────────┘
```

## 2. Module Separation

### 2.1 Backend Modules (FastAPI)

| Module | Responsibility | Key Components |
|--------|----------------|----------------|
| **Auth** | Register, login, JWT, RBAC middleware | `auth/router.py`, `auth/service.py`, `auth/deps.py` |
| **Data Management** | Dataset CRUD, file upload, prediction log storage | `data/router.py`, `data/service.py`, `data/repository.py` |
| **Preprocessing** | Clean, normalize, WQI, feature engineering | `preprocessing/service.py`, `preprocessing/wqi.py` |
| **ML Engine** | Train/predict: RF, LSTM, Isolation Forest | `ml/classification.py`, `ml/forecasting.py`, `ml/anomaly.py`, `ml/pipeline.py` |
| **Visualization & Alerts** | Dashboard aggregates, forecasts, anomalies, reports | `viz/router.py`, `viz/service.py`, `alerts/service.py` |

### 2.2 Frontend Modules (React)

| Module | Responsibility | Key Components |
|--------|----------------|----------------|
| **Auth** | Login, Register, protected routes | `AuthContext`, `LoginPage`, `RegisterPage` |
| **Dashboard** | Main dashboard layout and widgets | `DashboardPage`, `DashboardLayout` |
| **River Health** | River status and map | `RiverHealthPage`, `RiverMap`, `StatusCards` |
| **Data (Admin)** | Upload, manage datasets, run processing | `UploadDatasetPage`, `DatasetListPage`, `RunProcessingPage` |
| **Visualizations** | Time-series, forecast, map charts | `TimeSeriesChart`, `ForecastChart`, `RiverMapView` |
| **Alerts** | Early warning list and toasts | `AlertsPanel`, `AlertToast` |
| **Reports** | Export report UI | `ExportReportPage` or `ExportReportModal` |

### 2.3 Shared / Cross-Cutting

- **API client:** Axios/fetch with base URL and JWT injection  
- **RBAC:** Backend checks role on each request; frontend hides Admin-only menus/routes  
- **Config:** Environment variables for API URL, auth, DB, file paths  

## 3. Deployment View

- **Frontend:** Static build (e.g., `npm run build`) served by Nginx or same host as API.  
- **Backend:** FastAPI (Uvicorn) behind reverse proxy (Nginx).  
- **Database:** PostgreSQL on same server or managed service.  
- **File store:** Local directory or S3-compatible store for CSV and saved models.  
- **Optional:** Redis for session/cache; Celery for long-running ML jobs if needed.

## 4. Security Architecture

- **Authentication:** JWT access token (short-lived) + optional refresh token.  
- **Authorization:** Role claim in JWT; dependency in FastAPI that loads user and checks role (Admin vs Public).  
- **Data:** Passwords hashed with bcrypt; no sensitive data in logs.  
- **API:** CORS restricted to frontend origin; rate limiting on auth endpoints recommended.

---

*See DATABASE_SCHEMA.md, API_SPECIFICATION.md, and DATA_PIPELINE.md for next-level detail.*
