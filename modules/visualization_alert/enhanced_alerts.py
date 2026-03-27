"""
Enhanced alert rules for SmartRiver.

This add-on does not replace existing alert code. It only provides
new utility functions that can be called from Streamlit/UI code.
"""
from __future__ import annotations

from typing import List, Dict
import pandas as pd


def build_threshold_alerts(
    forecast_df: pd.DataFrame,
    threshold_wqi: float = 60.0,
    station_name: str = "Unknown Station",
) -> List[Dict]:
    """
    Trigger forecast alerts when predicted WQI < threshold.
    """
    if forecast_df is None or len(forecast_df) == 0:
        return []
    out = []
    for _, row in forecast_df.iterrows():
        wqi = float(row.get("predicted_wqi", 0))
        if wqi >= threshold_wqi:
            continue
        out.append({
            "alert_type": "ForecastThreshold",
            "severity": "high",
            "station_name": row.get("station_name", station_name),
            "date": str(row.get("date", ""))[:10],
            "wqi": round(wqi, 2),
            "message": f"Predicted WQI ({wqi:.2f}) is below threshold ({threshold_wqi:.1f}).",
        })
    return out


def build_anomaly_alerts(
    anomaly_df: pd.DataFrame,
    station_name: str = "Unknown Station",
) -> List[Dict]:
    """
    Trigger alerts for rows labeled as anomaly.
    """
    if anomaly_df is None or len(anomaly_df) == 0:
        return []
    out = []
    for _, row in anomaly_df.iterrows():
        if str(row.get("anomaly_label", "")).lower() != "anomaly":
            continue
        out.append({
            "alert_type": "Anomaly",
            "severity": "medium",
            "station_name": row.get("station_name", station_name),
            "date": str(row.get("date", row.get("reading_date", "")))[:10],
            "wqi": float(row.get("WQI", row.get("wqi", 0))),
            "message": "Isolation Forest detected an anomaly pattern.",
        })
    return out


def combine_alerts(threshold_alerts: List[Dict], anomaly_alerts: List[Dict]) -> List[Dict]:
    """
    Combine and deduplicate alerts by type + station + date.
    """
    merged = (threshold_alerts or []) + (anomaly_alerts or [])
    seen = set()
    out = []
    for a in merged:
        key = (a.get("alert_type"), a.get("station_name"), a.get("date"))
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    # Latest first for readability in UI.
    out.sort(key=lambda x: x.get("date", ""), reverse=True)
    return out

