# SmartRiver: Predictive River Pollution Monitoring System  
## Software Requirements Specification (SRS)

**Version:** 1.0  
**Date:** March 2025  
**Domain:** Intelligent Computing / Data Science  
**Data Source:** DOE Malaysia (Department of Environment Malaysia)

---

## 1. Introduction

### 1.1 Purpose
This document defines the complete software requirements and system architecture for **SmartRiver**, an AI and data science–driven system for monitoring and predicting river water quality in Malaysia using datasets from DOE Malaysia.

### 1.2 Scope
- **In scope:** Data management, preprocessing, ML-based classification/forecasting/anomaly detection, visualization, alerts, and user management for river water quality.
- **Out of scope:** Real-time sensor integration, mobile native apps, integration with external DOE APIs (system uses uploaded CSV datasets).

### 1.3 Definitions and Acronyms
| Term | Definition |
|------|-------------|
| WQI | Water Quality Index |
| DOE | Department of Environment (Malaysia) |
| LSTM | Long Short-Term Memory (neural network) |
| RBAC | Role-Based Access Control |
| Admin | User with full data and system management rights |
| Public User | User with view, alerts, and report export rights |

---

## 2. System Overview

SmartRiver consists of **four core modules**:

1. **Data Management Module** — Authentication, RBAC, CSV upload, dataset storage, prediction logs  
2. **Data Preprocessing Module** — Missing values, deduplication, normalization, WQI calculation, feature engineering  
3. **Machine Learning Engine Module** — Hybrid AI: Classification (Random Forest), Forecasting (LSTM), Anomaly Detection (Isolation Forest)  
4. **Visualization and Alert Module** — Dashboard, river health, time-series/forecast charts, map, alerts, report export  

---

## 3. Functional Requirements

### 3.1 User Features (Summary)

| Feature | Admin | Public User |
|---------|-------|-------------|
| Register account | ✓ | ✓ |
| Login account | ✓ | ✓ |
| View dashboard | ✓ | ✓ |
| View river health | ✓ | ✓ |
| Upload dataset | ✓ | — |
| Run data processing | ✓ | — |
| Receive early warning alert | ✓ | ✓ |
| Export report | ✓ | ✓ |
| Manage datasets | ✓ | — |
| Manage users (optional) | ✓ | — |

### 3.2 Module 1: Data Management

| ID | Requirement | Priority |
|----|-------------|----------|
| DM-1 | System shall provide user registration with email and password | High |
| DM-2 | System shall provide login and JWT-based session handling | High |
| DM-3 | System shall enforce Role-Based Access Control (Admin, Public User) | High |
| DM-4 | Admin shall be able to upload CSV dataset (DOE format) | High |
| DM-5 | System shall persist uploaded datasets in PostgreSQL | High |
| DM-6 | Admin shall be able to list, view, update, and delete datasets | High |
| DM-7 | System shall store all prediction logs (classification, forecast, anomaly) with timestamps and user/session | High |

### 3.3 Module 2: Data Preprocessing

| ID | Requirement | Priority |
|----|-------------|----------|
| DP-1 | System shall handle missing values (configurable: drop or impute) | High |
| DP-2 | System shall remove duplicate records | High |
| DP-3 | System shall support data normalization (e.g., Min-Max, StandardScaler) | High |
| DP-4 | System shall compute Water Quality Index (WQI) from DOE parameters | High |
| DP-5 | System shall support feature engineering (e.g., rolling stats, lag features for ML) | High |

### 3.4 Module 3: Machine Learning Engine

| ID | Requirement | Priority |
|----|-------------|----------|
| ML-1 | **Classification:** Random Forest model to classify river status as Clean / Slightly Polluted / Polluted | High |
| ML-2 | **Forecasting:** LSTM model to predict WQI 7–30 days ahead | High |
| ML-3 | **Anomaly Detection:** Isolation Forest to detect abnormal pollution spikes | High |
| ML-4 | System shall allow Admin to trigger training/re-training and prediction runs | High |
| ML-5 | All model outputs shall be stored as prediction logs | High |

### 3.5 Module 4: Visualization and Alert

| ID | Requirement | Priority |
|----|-------------|----------|
| VA-1 | Interactive dashboard with key metrics and charts | High |
| VA-2 | River health visualization (status by location/time) | High |
| VA-3 | Time-series chart of WQI and parameters | High |
| VA-4 | Forecast chart (7–30 days ahead) | High |
| VA-5 | Map visualization (e.g., Leaflet) for river stations/locations | High |
| VA-6 | Alert system when anomaly is detected (on-screen and/or stored for “early warning”) | High |
| VA-7 | Export report (e.g., PDF/CSV) for dashboard or selected data | High |

---

## 4. Non-Functional Requirements

- **Performance:** Dashboard load &lt; 3 s; ML prediction response &lt; 30 s for single run where applicable.  
- **Security:** Passwords hashed (e.g., bcrypt); JWT for API auth; RBAC on all protected endpoints.  
- **Usability:** Clean, modern UI; responsive layout (desktop-first, usable on tablet).  
- **Maintainability:** Modular backend (routers, services); clear separation between API, ML, and data layers.

---

## 5. Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React.js, TailwindCSS |
| Backend | Python, FastAPI |
| ML | Python, Scikit-learn, TensorFlow/Keras |
| Database | PostgreSQL |
| Visualization | Plotly / Chart.js, Leaflet |
| Auth | JWT (e.g., python-jose, passlib) |

---

## 6. References

- DOE Malaysia water quality monitoring and WQI documentation.  
- Malaysian WQI formula (DOE): typically based on sub-indices (DO, BOD, COD, NH3-N, TSS, pH).

---

*End of SRS — See companion documents for Architecture, Database Schema, API Design, Folder Structure, Data Pipeline, UI Pages, and ML Workflow.*
