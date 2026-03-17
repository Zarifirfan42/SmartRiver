"""
Run anomaly detection (Isolation Forest) on a DataFrame or CSV path.
Returns anomalies with date, station_code, wqi, reason for storage and API.
"""
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]


def run_anomaly_detection(
    df=None,
    input_path: Optional[Path] = None,
) -> list[dict]:
    """
    Run anomaly detection on the given DataFrame or file.
    If df is None, input_path must be set and CSV will be loaded (with WQI).
    Returns list of { date, station_code, wqi, reason, score } and saves to prediction_log + alerts.
    """
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    import pandas as pd
    import joblib
    from backend.db.repository import save_prediction_log, save_alert

    if df is None:
        if not input_path or not Path(input_path).exists():
            return []
        df = pd.read_csv(input_path)

    model_path = ROOT / "ml_models" / "anomaly_detection" / "model.joblib"
    if not model_path.exists():
        return []

    try:
        data = joblib.load(model_path)
        model = data["model"]
        features = data["feature_columns"]
    except Exception:
        return []

    cols = [c for c in features if c in df.columns]
    if not cols:
        return []

    X = df[cols].fillna(0)
    pred = model.predict(X)
    scores = model.decision_function(X)

    date_col = "date" if "date" in df.columns else None
    station_col = "station_code" if "station_code" in df.columns else None
    wqi_col = "WQI" if "WQI" in df.columns else "wqi" if "wqi" in df.columns else None

    anomalies = []
    for i in range(len(df)):
        if pred[i] != -1:
            continue
        rec = {
            "index": i,
            "score": float(scores[i]),
            "reason": "Abnormal spike",
        }
        if date_col:
            d = df.iloc[i][date_col]
            rec["date"] = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d).split(" ")[0][:10]
        else:
            rec["date"] = ""
        if station_col:
            rec["station_code"] = str(df.iloc[i][station_col]).strip()
        else:
            rec["station_code"] = "—"
        if wqi_col and wqi_col in df.columns:
            try:
                rec["wqi"] = float(df.iloc[i][wqi_col])
            except (TypeError, ValueError):
                rec["wqi"] = None
        else:
            rec["wqi"] = None
        anomalies.append(rec)

    if anomalies:
        save_prediction_log(
            "anomaly",
            {"anomalies": anomalies, "count": len(anomalies)},
            model_name="isolation_forest",
        )

    return anomalies
