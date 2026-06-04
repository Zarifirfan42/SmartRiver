"""Verify 2026 LSTM WQI values in SQLite (run from project root with PYTHONPATH=.)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.repository import verify_wqi_predictions_2026  # noqa: E402


def main() -> None:
    result = verify_wqi_predictions_2026()
    print(result.get("message", ""))
    for row in result.get("by_station") or []:
        print(
            f"Station {row.get('station_code')}: "
            f"min={float(row.get('min_wqi') or 0):.1f} "
            f"max={float(row.get('max_wqi') or 0):.1f} "
            f"avg={float(row.get('avg_wqi') or 0):.1f} "
            f"total={row.get('total')}"
        )
    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
