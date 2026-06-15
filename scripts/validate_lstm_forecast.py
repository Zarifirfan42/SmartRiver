"""Validate per-station LSTM 2026 forecasts have realistic WQI ranges (run after retrain)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_forecast_by_station(station_code: str) -> list[dict]:
    from backend.db.repository import get_latest_forecast

    rows = get_latest_forecast(station_code=station_code, limit=5000)
    return [r for r in rows if str(r.get("date", ""))[:4] == "2026"]


def main() -> int:
    checks = [
        ("S04", 70.0, "Sungai Kulim should forecast Clean/near-Clean"),
        ("S02", 35.0, "Sungai Gombak mean should not be near-zero"),
    ]

    failed = False
    for code, min_mean, label in checks:
        rows = get_forecast_by_station(code)
        if not rows:
            print(f"FAIL {code}: no 2026 forecast rows — retrain LSTM and run forecast first.")
            failed = True
            continue
        wqis = [float(r.get("wqi") or 0) for r in rows]
        mean_w = sum(wqis) / len(wqis)
        std_w = (sum((w - mean_w) ** 2 for w in wqis) / max(len(wqis) - 1, 1)) ** 0.5
        print(f"{code}: n={len(wqis)} mean={mean_w:.1f} std={std_w:.2f} min={min(wqis):.1f} max={max(wqis):.1f}")
        if mean_w < min_mean:
            print(f"  FAIL: {label} (mean {mean_w:.1f} < {min_mean})")
            failed = True
        if std_w < 2.0:
            print(f"  FAIL: forecast too flat (std {std_w:.2f} < 2.0)")
            failed = True

    # Cross-station variance: not all stations identical
    means = {}
    for code in ("S01", "S02", "S04", "S06", "S07"):
        rows = get_forecast_by_station(code)
        if rows:
            means[code] = sum(float(r.get("wqi") or 0) for r in rows) / len(rows)
    if len(means) >= 2 and max(means.values()) - min(means.values()) < 5.0:
        print(f"FAIL: all stations too similar: {means}")
        failed = True
    elif means:
        print(f"Station means: { {k: round(v, 1) for k, v in means.items()} }")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
