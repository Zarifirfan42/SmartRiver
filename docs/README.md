# SmartRiver — Documentation Index

**SmartRiver: Predictive River Pollution Monitoring System**  
Final Year Project — Intelligent Computing / Data Science  
Data source: DOE Malaysia

---

## Documents

| Document | Description |
|----------|-------------|
| [SRS_SmartRiver.md](SRS_SmartRiver.md) | **Software Requirements Specification** — scope, functional/non-functional requirements, user features, technology stack |
| [ARCHITECTURE.md](ARCHITECTURE.md) | **System architecture** — high-level diagram, module separation (backend + frontend), deployment, security |
| [DATA_PIPELINE.md](DATA_PIPELINE.md) | **Data pipeline** — end-to-end flow from upload → preprocessing → ML → dashboard/alerts/export |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | **Database overview** — entities, relationships, enums |
| [database_schema.sql](database_schema.sql) | **PostgreSQL schema** — executable SQL to create tables, indexes, triggers |
| [API_SPECIFICATION.md](API_SPECIFICATION.md) | **API design** — REST endpoints for auth, data, preprocessing, ML, dashboard, alerts, reports |
| [FOLDER_STRUCTURE.md](FOLDER_STRUCTURE.md) | **Folder structure** — recommended backend (FastAPI) and frontend (React) layout |
| [ML_WORKFLOW.md](ML_WORKFLOW.md) | **ML workflow** — WQI formula, Random Forest, LSTM, Isolation Forest steps and hyperparameters |
| [UI_PAGES.md](UI_PAGES.md) | **UI pages and dashboard** — routes, pages, dashboard components, design guidelines |

---

## Quick reference

- **4 modules:** Data Management, Data Preprocessing, ML Engine (RF + LSTM + Isolation Forest), Visualization & Alert  
- **Stack:** React + TailwindCSS (frontend), Python FastAPI (backend), Scikit-learn + TensorFlow/Keras (ML), PostgreSQL (DB), Plotly/Chart.js + Leaflet (viz)  
- **Users:** Register, Login, View dashboard, View river health, Export report, Receive alerts; **Admin only:** Upload dataset, Run processing  

Use this index to navigate the full system design for implementation and FYP reporting.
