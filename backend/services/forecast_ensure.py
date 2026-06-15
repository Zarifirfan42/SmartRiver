"""Ensure LSTM 2026 forecast exists before dashboard reads (Render cold start / background failures)."""
from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_last_attempt_at: float = 0.0
_MIN_RETRY_SECONDS = 120.0
_scheduled = False


def _has_dated_forecast() -> bool:
    from backend.db.repository import _latest_dashboard_forecast_log

    log = _latest_dashboard_forecast_log()
    if not log:
        return False
    pts = (log.get("result_json") or {}).get("forecast") or []
    return any(isinstance(f, dict) and len((f.get("date") or "").strip()) >= 10 for f in pts)


def schedule_forecast_if_needed() -> None:
    """Non-blocking: kick off LSTM forecast when logs/SQLite have no dated points."""
    global _scheduled
    if _has_dated_forecast():
        return
    with _lock:
        if _scheduled or _has_dated_forecast():
            return
        _scheduled = True

        def _run() -> None:
            global _scheduled
            try:
                ensure_forecast_generated(force=True)
            finally:
                _scheduled = False

        threading.Thread(target=_run, daemon=True).start()


def ensure_forecast_generated(*, force: bool = False) -> bool:
    """
    Run LSTM forecast if prediction_logs are empty.
    Returns True when dated forecast points exist (before or after this call).
    """
    global _last_attempt_at

    if not force and _has_dated_forecast():
        return True

    now = time.monotonic()
    if not force and (now - _last_attempt_at) < _MIN_RETRY_SECONDS:
        return _has_dated_forecast()

    with _lock:
        if not force and _has_dated_forecast():
            return True
        if not force and (time.monotonic() - _last_attempt_at) < _MIN_RETRY_SECONDS:
            return _has_dated_forecast()

        _last_attempt_at = time.monotonic()
        try:
            from backend.services.forecast_service import run_forecast

            pts = run_forecast() or []
            n = len(pts)
            print(f"ensure_forecast_generated: {n} forecast points saved.")
            return n > 0 or _has_dated_forecast()
        except Exception as exc:
            logger.exception("ensure_forecast_generated failed: %s", exc)
            print("ensure_forecast_generated failed:", exc)
            return _has_dated_forecast()


def run_forecast_with_retries(attempts: int = 3, delay_seconds: float = 45.0) -> int:
    """Startup helper — retry LSTM forecast (TensorFlow may need time after container boot)."""
    total = 0
    for i in range(max(1, attempts)):
        try:
            from backend.services.forecast_service import run_forecast

            total = len(run_forecast() or [])
            if total > 0:
                print(f"run_forecast_with_retries: success on attempt {i + 1} ({total} points).")
                return total
        except Exception as exc:
            print(f"run_forecast_with_retries attempt {i + 1} failed:", exc)
        if i < attempts - 1:
            time.sleep(delay_seconds)
    return total
