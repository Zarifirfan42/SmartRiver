"""
Recompute derived analytics when the in-memory readings store changes (upload, delete, filesystem reload).
Forecast is stored in prediction_logs; without a refresh, the Pollution Forecast page stays stale.
"""
import logging

logger = logging.getLogger(__name__)


def refresh_forecast_after_readings_change() -> None:
    try:
        from backend.services.forecast_service import run_forecast

        run_forecast()
        logger.info("Forecast recomputed after readings change")
    except Exception as exc:
        logger.warning("Forecast refresh skipped: %s", exc)
