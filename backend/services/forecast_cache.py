"""Bundled LSTM 2026 forecast cache — instant load on Render when live inference is slow."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "datasets" / "cache" / "lstm_forecast_2026.json"


def load_forecast_cache() -> Optional[list[dict]]:
    if not CACHE_PATH.is_file():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        pts = data.get("forecast") or []
        dated = [p for p in pts if isinstance(p, dict) and len((p.get("date") or "")[:10]) >= 10]
        if len(dated) < 100:
            return None
        print(f"load_forecast_cache: {len(dated)} points from {CACHE_PATH.name}")
        return dated
    except Exception as exc:
        logger.warning("load_forecast_cache failed: %s", exc)
        return None


def save_forecast_cache(forecast: list[dict]) -> None:
    if not forecast:
        return
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.utcnow().isoformat(),
            "model": "lstm",
            "forecast": forecast,
        }
        CACHE_PATH.write_text(json.dumps(payload, indent=0), encoding="utf-8")
        print(f"save_forecast_cache: wrote {len(forecast)} points to {CACHE_PATH}")
    except Exception as exc:
        logger.warning("save_forecast_cache failed: %s", exc)
