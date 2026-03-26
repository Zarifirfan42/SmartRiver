"""FastAPI app entry: CORS, router includes, lifespan."""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure project root is on path so backend.* and modules work when running from backend/
_root = Path(__file__).resolve().parents[2]
if _root and str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup: seed default admin, load default dataset, run anomaly if model exists."""
    try:
        from backend.db.repository import seed_default_admin
        admin = seed_default_admin()
        if admin:
            print("Default admin created: admin@smartriver.com")
    except Exception as e:
        print("Seed admin skipped:", e)
    try:
        from backend.services.dataset_loader import run_startup_data_load
        run_startup_data_load()
        print("Default dataset loaded; stations and WQI data ready.")
    except Exception as e:
        print("Dataset load skipped:", e)
    try:
        from backend.services.live_simulation import start_daily_scheduler
        start_daily_scheduler()
    except Exception as e:
        print("Live simulation scheduler skipped:", e)
    yield


# from data_management.controllers.auth_controller import router as auth_router
# from data_management.controllers.dataset_controller import router as dataset_router
# from data_preprocessing.controllers.preprocessing_controller import router as preprocessing_router
# from ml_engine.controllers.ml_controller import router as ml_router
# from visualization_alert.controllers.dashboard_controller import router as dashboard_router
# from visualization_alert.controllers.alert_controller import router as alert_router
# from visualization_alert.controllers.report_controller import router as report_router

app = FastAPI(
    title="SmartRiver API",
    description="Predictive River Pollution Monitoring System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
# app.include_router(dataset_router, prefix="/api/v1/datasets", tags=["Data Management"])
# app.include_router(preprocessing_router, prefix="/api/v1/preprocessing", tags=["Preprocessing"])
# app.include_router(ml_router, prefix="/api/v1/ml", tags=["ML Engine"])
# app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
# app.include_router(alert_router, prefix="/api/v1/alerts", tags=["Alerts"])
# Optional: wire new backend api/auth/controllers
try:
    from backend.api.routes import register_routes
    register_routes(app)
except ImportError as e:
    print("Warning: register_routes failed:", e)

# Legacy alias for dataset records (requested: GET /api/water-quality)
try:
    from backend.controllers.water_quality_controller import router as wq_router
    app.include_router(wq_router, prefix="/api/water-quality", tags=["Water Quality"])
except Exception as e:
    print("Warning: /api/water-quality could not be loaded:", e)

# Ensure auth is always mounted (login/register) even if routes had a partial failure
try:
    from backend.controllers.auth_controller import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
except Exception as e:
    print("Warning: Auth routes could not be loaded:", e)


@app.get("/")
def root():
    return {
        "message": "SmartRiver API",
        "docs": "/docs",
        "app": "Open the web app at http://localhost:3000 for login, dashboard, and all pages.",
    }


# Redirect browser users who hit the API URL to the frontend app
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


@app.get("/login")
def redirect_login():
    return RedirectResponse(url=f"{FRONTEND_URL}/login", status_code=302)


@app.get("/register")
def redirect_register():
    return RedirectResponse(url=f"{FRONTEND_URL}/register", status_code=302)


@app.get("/dashboard")
def redirect_dashboard():
    return RedirectResponse(url=f"{FRONTEND_URL}/dashboard", status_code=302)


@app.get("/health")
def health():
    return {"status": "ok"}
