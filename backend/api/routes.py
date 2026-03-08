"""
API routes — Central route registration for SmartRiver backend.
Register all API routers under /api/v1.
"""
from fastapi import APIRouter
from backend.api import api_router


def register_routes(app):
    """Register all API routes on the FastAPI app. Call from main.py."""
    try:
        from backend.controllers.water_quality_controller import router as wq_router
        api_router.include_router(wq_router, prefix="/water-quality", tags=["Water Quality"])
    except ImportError:
        pass
    try:
        from backend.controllers.dashboard_controller import router as dashboard_router
        api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
    except ImportError:
        pass
    try:
        from backend.controllers.preprocessing_controller import router as prep_router
        api_router.include_router(prep_router, prefix="/preprocessing", tags=["Preprocessing"])
    except ImportError:
        pass
    try:
        from backend.controllers.ml_controller import router as ml_router
        api_router.include_router(ml_router, prefix="/ml", tags=["ML Engine"])
    except ImportError:
        pass
    try:
        from backend.controllers.alert_controller import router as alert_router
        api_router.include_router(alert_router, prefix="/alerts", tags=["Alerts"])
    except ImportError:
        pass
    try:
        from backend.controllers.dataset_controller import router as dataset_router
        api_router.include_router(dataset_router, prefix="/datasets", tags=["Datasets"])
    except ImportError:
        pass
    app.include_router(api_router, prefix="/api/v1")
