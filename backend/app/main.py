"""FastAPI app entry: CORS, router includes, lifespan."""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure project root is on path so backend.* and modules work when running from backend/
_root = Path(__file__).resolve().parents[2]
if _root and str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Load .env before any code reads SMARTRIVER_OTP_DEV_LOG / SMTP_* (email_service, JWT, etc.)
try:
    from dotenv import load_dotenv

    # backend/.env first, then root .env with override=True so root is canonical for SMTP_* / secrets
    load_dotenv(_root / "backend" / ".env")
    load_dotenv(_root / ".env", override=True)
except ImportError:
    pass

if (os.environ.get("SMARTRIVER_OTP_DEV_LOG") or "").strip() in ("1", "true", "yes", "on"):
    print("📧 SmartRiver: SMARTRIVER_OTP_DEV_LOG is on — OTP codes will print to this console.")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup: seed default admin, load default dataset, run anomaly if model exists.

    Auth routes do not load ML models or datasets per request; heavy work happens here once.
    On Render, SMARTRIVER_DEFER_FORECAST moves dataset load + forecast to a background thread
    so /health responds before Excel ingest and LSTM inference finish.
    """
    _api_port = os.environ.get("SMARTRIVER_API_PORT", os.environ.get("PORT", "8000"))
    print("✅ SmartRiver API starting on port " + str(_api_port))

    try:
        from backend.db.repository import verify_auth_database_connection

        verify_auth_database_connection()
    except Exception as e:
        print("❌ Database startup check failed:", e)
    try:
        from backend.db.repository import seed_default_admin

        admin = seed_default_admin()
        if admin:
            print("Default admin created: admin@smartriver.com")
    except Exception as e:
        print("Seed admin skipped:", e)

    defer_heavy = (os.environ.get("SMARTRIVER_DEFER_FORECAST") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    def _heavy_startup() -> None:
        try:
            from backend.services.dataset_loader import run_startup_data_load

            run_startup_data_load()
            from backend.db.repository import migrate_store_river_names

            migrate_store_river_names()
            print("Default dataset loaded; stations and WQI data ready.")
        except Exception as e:
            print("Dataset load skipped:", e)

        # Fast path: hydrate forecast from bundled cache so dashboard predictions show immediately.
        try:
            from backend.services.forecast_service import run_forecast

            n = len(run_forecast() or [])
            if n > 0:
                print(f"Forecast ready: {n} points (cache or LSTM).")
        except Exception as e:
            print("Initial forecast load skipped:", e)

        try:
            from backend.services.live_simulation import start_daily_scheduler

            start_daily_scheduler()
        except Exception as e:
            print("Live simulation scheduler skipped:", e)

        if defer_heavy:
            try:
                from backend.db.repository import _latest_dashboard_forecast_log
                from backend.services.forecast_ensure import run_forecast_with_retries

                if not _latest_dashboard_forecast_log():
                    n = run_forecast_with_retries(attempts=2, delay_seconds=60.0)
                    print(f"Background forecast retry complete: {n} points.")
            except Exception as exc:
                print("Background forecast retry failed:", exc)

    if defer_heavy:
        import threading

        threading.Thread(target=_heavy_startup, daemon=True).start()
        print("Dataset + LSTM startup scheduled in background (SMARTRIVER_DEFER_FORECAST).")
    else:
        _heavy_startup()

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

# CORS: allow_origins=["*"] with allow_credentials=True is invalid in browsers — use * + False for Bearer-token APIs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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

# Production: serve built React app from frontend/dist (same origin as API)
_FRONTEND_DIST = _root / "frontend" / "dist"
_SPA_MODE = _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").is_file()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    """Health check under /api so Vite proxy /api → backend can verify connectivity."""
    return {"status": "ok"}


if not _SPA_MODE:

    @app.get("/")
    def root():
        return {
            "message": "SmartRiver API",
            "docs": "/docs",
            "app": "Open the web app at http://localhost:3000 for login, dashboard, and all pages.",
        }

    @app.get("/login")
    def redirect_login():
        return RedirectResponse(url=f"{FRONTEND_URL}/login", status_code=302)

    @app.get("/register")
    def redirect_register():
        return RedirectResponse(url=f"{FRONTEND_URL}/register", status_code=302)

    @app.get("/dashboard")
    def redirect_dashboard():
        return RedirectResponse(url=f"{FRONTEND_URL}/dashboard", status_code=302)

else:
    import mimetypes

    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    _asset_count = len(list((_FRONTEND_DIST / "assets").glob("*"))) if (_FRONTEND_DIST / "assets").is_dir() else 0
    print(f"SPA mode ON: {_FRONTEND_DIST} ({_asset_count} files in assets/)")

    def _dist_file_response(rel_path: str) -> FileResponse:
        target = (_FRONTEND_DIST / rel_path).resolve()
        root = _FRONTEND_DIST.resolve()
        if not str(target).startswith(str(root)) or not target.is_file():
            raise HTTPException(status_code=404, detail="Not found")
        media_type, _ = mimetypes.guess_type(str(target))
        return FileResponse(target, media_type=media_type or "application/octet-stream")

    @app.get("/assets/{asset_path:path}")
    def serve_frontend_asset(asset_path: str):
        return _dist_file_response(f"assets/{asset_path}")

    @app.get("/images/{image_path:path}")
    def serve_frontend_image(image_path: str):
        return _dist_file_response(f"images/{image_path}")

    @app.get("/")
    def spa_root():
        return _dist_file_response("index.html")

    @app.get("/{spa_path:path}")
    def spa_fallback(spa_path: str):
        if spa_path.startswith("api") or spa_path in ("docs", "openapi.json", "redoc", "health"):
            raise HTTPException(status_code=404)
        candidate = f"{spa_path}"
        target = (_FRONTEND_DIST / candidate).resolve()
        root = _FRONTEND_DIST.resolve()
        if spa_path and str(target).startswith(str(root)) and target.is_file():
            return _dist_file_response(candidate)
        return _dist_file_response("index.html")
