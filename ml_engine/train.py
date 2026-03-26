"""
Train SmartRiver ML models (Random Forest, LSTM, Isolation Forest).

Requirements (from project root):
- Input CSV: placed in `datasets/` (DOE Malaysia format; columns will be normalized)
- Preprocessing: uses `data_preprocessing.services.pipeline.run_pipeline`
- Outputs:
  - Random Forest  -> ml_models/random_forest/model.joblib
  - LSTM           -> ml_models/lstm/model.keras
  - IsolationForest-> ml_models/anomaly_detection/model.joblib
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _find_default_csv(datasets_dir: Path) -> Path:
    datasets_dir = Path(datasets_dir)
    if not datasets_dir.exists():
        raise FileNotFoundError(f"datasets directory not found: {datasets_dir}")

    # Prefer top-level CSVs (not uploads)
    candidates = sorted([p for p in datasets_dir.glob("*.csv") if p.is_file()])
    if candidates:
        return candidates[0]

    # Fall back to latest uploaded CSV
    uploads = datasets_dir / "uploads"
    up = sorted([p for p in uploads.glob("*.csv") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    if up:
        return up[0]

    raise FileNotFoundError(f"No CSV found in {datasets_dir} or {uploads}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train SmartRiver models from DOE Malaysia CSV in datasets/.")
    parser.add_argument("--datasets-dir", type=Path, default=PROJECT_ROOT / "datasets", help="Datasets directory (default: ./datasets)")
    parser.add_argument("--csv", type=str, default=None, help="CSV filename inside datasets-dir (default: first CSV found)")
    parser.add_argument("--missing-strategy", choices=["mean", "median", "drop"], default="median")
    parser.add_argument("--no-normalize", action="store_true", help="Disable feature normalization in preprocessing")
    parser.add_argument("--lstm-seq-len", type=int, default=30)
    parser.add_argument("--lstm-horizon", type=int, default=7)
    parser.add_argument("--lstm-epochs", type=int, default=50)
    parser.add_argument("--lstm-station", type=str, default=None, help="Optional station_code to train LSTM on")
    args = parser.parse_args()

    datasets_dir: Path = args.datasets_dir
    if args.csv:
        csv_path = (datasets_dir / args.csv).with_suffix(".csv")
    else:
        csv_path = _find_default_csv(datasets_dir)

    from data_preprocessing.services.pipeline import run_pipeline
    from ml_engine.services.classification_service import train as train_rf, save_model as save_rf
    from ml_engine.services.forecasting_service import train as train_lstm
    from ml_engine.services.anomaly_service import train as train_anom, save_model as save_anom

    print(f"Loading CSV: {csv_path}")
    df = run_pipeline(
        csv_path,
        output_path=None,
        missing_strategy=args.missing_strategy,
        remove_duplicates=True,
        rolling_window=7,
        lag_days=(1, 7, 14),
        normalize=not args.no_normalize,
    )

    out_root = PROJECT_ROOT / "ml_models"
    out_root.mkdir(parents=True, exist_ok=True)

    # 1) Random Forest
    rf_out = train_rf(df)
    rf_path = out_root / "random_forest" / "model.joblib"
    save_rf(rf_out["model"], rf_out["feature_columns"], rf_path)
    print(f"Saved Random Forest: {rf_path}")

    # 2) LSTM
    lstm_dir = out_root / "lstm"
    lstm_dir.mkdir(parents=True, exist_ok=True)
    lstm_out = train_lstm(
        df,
        station_code=args.lstm_station,
        seq_len=args.lstm_seq_len,
        horizon=args.lstm_horizon,
        epochs=args.lstm_epochs,
        verbose=1,
    )
    if lstm_out.get("error"):
        print(f"Skipped LSTM: {lstm_out['error']}")
    else:
        # Save directly to requested file name `model.keras`
        model_file = lstm_dir / "model.keras"
        lstm_out["model"].save(model_file)
        # Keep scaler/config alongside (useful for inference)
        import joblib

        joblib.dump(
            {"scaler": lstm_out.get("scaler"), "config": {"seq_len": args.lstm_seq_len, "horizon": args.lstm_horizon}},
            lstm_dir / "scaler.joblib",
        )
        print(f"Saved LSTM: {model_file}")

    # 3) Isolation Forest (anomaly detection)
    an_out = train_anom(df)
    an_path = out_root / "anomaly_detection" / "model.joblib"
    save_anom(an_out["model"], an_out["feature_columns"], an_path)
    print(f"Saved Isolation Forest: {an_path}")

    # Print a small summary
    print("Done.")
    print("RF metrics:", rf_out.get("metrics"))
    if not lstm_out.get("error"):
        print("LSTM metrics:", lstm_out.get("metrics"))
    print("Anomaly samples:", len(df))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

