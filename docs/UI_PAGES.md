# SmartRiver — UI Pages & Dashboard Components

## 1. Page List and Routes

| Route | Page | Auth | Role | Description |
|-------|------|------|------|-------------|
| `/login` | LoginPage | No | — | Email + password; redirect to dashboard after login |
| `/register` | RegisterPage | No | — | Email, password, full name; then redirect to login |
| `/` or `/dashboard` | DashboardPage | Yes | All | Main dashboard with summary and charts |
| `/river-health` | RiverHealthPage | Yes | All | River status by station; table + optional map |
| `/alerts` | AlertsPage | Yes | All | List of early warning alerts; mark as read |
| `/export` | ExportReportPage | Yes | All | Select dataset/date range/format; trigger download |
| `/datasets` | DatasetListPage | Yes | Admin | List datasets; link to upload and run processing |
| `/datasets/upload` | UploadDatasetPage | Yes | Admin | Upload CSV; optional name/description |
| `/datasets/:id/process` | RunProcessingPage | Yes | Admin | Run preprocessing + ML (classification, forecast, anomaly); show progress/result |

---

## 2. Dashboard Components

### 2.1 Layout

- **AppLayout:** Sidebar (nav links by role) + top header (user menu, logo) + main content area (outlet).  
- **Sidebar:** Dashboard, River Health, Alerts, Export Report; Admin: Datasets, Upload, Run Processing.  
- **Header:** “SmartRiver” title, user name, logout.

### 2.2 DashboardPage (main dashboard)

- **Summary cards (top row):**
  - Total stations
  - Date range of data
  - Average WQI (latest or selected period)
  - Count by status: Clean / Slightly Polluted / Polluted
  - Recent anomalies count
- **Charts (below):**
  - **Time-series chart:** WQI (and optionally DO, BOD) over time; filter by station and date range (Plotly or Chart.js).
  - **Forecast chart:** Predicted WQI for next 7–30 days (from latest forecast run).
  - **Status distribution:** Pie or bar — Clean vs Slightly Polluted vs Polluted.
- **Map (optional):** Leaflet map with stations colored by latest status (green / yellow / red).

### 2.3 RiverHealthPage

- **Filters:** Dataset, station, date range.  
- **Table:** Station code, date, WQI, river status, key parameters.  
- **RiverMap:** Stations on map with popup (latest WQI, status).  
- Optional: small time-series per station (inline or modal).

### 2.4 Charts (reusable)

| Component | Library | Purpose |
|-----------|---------|---------|
| TimeSeriesChart | Plotly / Chart.js | WQI and parameters over time; multi-line; date axis |
| ForecastChart | Plotly / Chart.js | Historical + forecast WQI; distinct style for forecast segment |
| StatusPieChart | Chart.js / Plotly | Clean / Slightly Polluted / Polluted counts |
| RiverMap | Leaflet | Markers by station; color by status; popup with details |

### 2.5 Alerts

- **AlertsPanel:** List of alerts (station, message, severity, time); “Mark as read”; filter unread.  
- **AlertToast:** Toast/notification when new anomaly is detected (if real-time or on page load).  
- **AlertsPage:** Full-page list with same AlertsPanel and optional export.

### 2.6 Data management (Admin)

- **UploadDatasetPage:** Drag-and-drop or file input; name, description; submit → success message and link to dataset list.  
- **DatasetListPage:** Table (name, size, rows, uploaded at, actions); actions: View, Run processing, Delete.  
- **RunProcessingPage:** Select dataset; checkboxes for Preprocess, Classification, Forecast, Anomaly; “Run” → progress or result summary (e.g. “Preprocessing done; Classification done; 3 anomalies found”).

### 2.7 Export

- **ExportReportPage (or modal):** Select dataset, date range, station (optional), format (CSV/PDF); “Export” → download file.

---

## 3. Design Guidelines

- **Clean and modern:** Plenty of whitespace; consistent spacing (e.g. Tailwind).  
- **Color coding:** Green = Clean, Yellow/Orange = Slightly Polluted, Red = Polluted; blue for primary actions.  
- **Responsive:** Desktop-first; sidebar collapses to hamburger on small screens; tables scroll horizontally if needed.  
- **Accessibility:** Labels, contrast, focus states; ARIA where helpful.  
- **Loading and errors:** Spinners/skeletons while fetching; error banners with retry.

---

## 4. Tech Stack (UI)

- **React** (with Router for routes).  
- **TailwindCSS** for layout and styling.  
- **Plotly (react-plotly.js) or Chart.js** for time-series and forecast.  
- **Leaflet (react-leaflet)** for map.  
- **Axios** or fetch for API; central client with JWT in header.  
- **Context (AuthContext)** for user and login state; ProtectedRoute for auth-required pages.

---

*Use this as the checklist for implementing frontend pages and dashboard components.*
