"""FastAPI app entry: CORS, router includes, lifespan."""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure project root is on path so backend.* and modules work when running from backend/
_root = Path(__file__).resolve().parents[2]
if _root and str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup: seed default admin if not present."""
    try:
        from backend.db.repository import seed_default_admin
        admin = seed_default_admin()
        if admin:
            print("Default admin created: admin@smartriver.com")
    except Exception as e:
        print("Seed admin skipped:", e)
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
except ImportError:
    pass


@app.get("/")
def root():
    return {"message": "SmartRiver API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
