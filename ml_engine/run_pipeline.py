#!/usr/bin/env python3
"""
Run the full SmartRiver ML pipeline: generate sample data → preprocess → train all models → print metrics.
Usage (from project root):
  python -m ml_engine.run_pipeline [--csv path] [--output-dir path]
"""
import argparse
import sys
from pathlib import Path

# Ensure project root is on path
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import numpy as np
import pandas as pd

from data_preprocessing.services.pipeline import run_pipeline
from ml_engine.services.training_pipeline import run_training_pipeline


def generate_sample_csv(path: Path, n_rows: int = 2000) -> None:
    """Generate a sample DOE-style CSV for testing."""
    np.random.seed(42)
    n = n_rows
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    stations = [f"S{i:02d}" for i in np.random.randint(1, 6, n)]
    # DOE parameters (rough realistic ranges)
    do = np.clip(np.random.normal(6, 2, n), 0.5, 10)
    bod = np.clip(np.random.exponential(2, n), 0.1, 15)
    cod = np.clip(np.random.exponential(15, n), 1, 80)
    an = np.clip(np.random.exponential(0.5, n), 0.01, 5)
    tss = np.clip(np.random.exponential(30, n), 1, 200)
    ph = np.clip(np.random.normal(7, 0.8, n), 5, 9)

    df = pd.DataFrame({
        "date": dates,
        "station_code": stations,
        "DO": do,
        "BOD": bod,
        "COD": cod,
        "AN": an,
        "TSS": tss,
        "pH": ph,
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Generated sample CSV: {path} ({len(df)} rows)")


def main():
    parser = argparse.ArgumentParser(description="SmartRiver ML pipeline")
    parser.add_argument("--csv", type=Path, default=None, help="Input CSV path (default: generate sample)")
    parser.add_argument("--output-dir", type=Path, default=_project_root / "ml_models", help="Output directory for models")
    parser.add_argument("--no-lstm", action="store_true", help="Skip LSTM training (if TensorFlow not installed)")
    args = parser.parse_args()

    csv_path = args.csv
    if csv_path is None:
        csv_path = _project_root / "datasets" / "sample_water_quality.csv"
        generate_sample_csv(csv_path)

    if not csv_path.exists():
        print(f"Error: CSV not found: {csv_path}")
        sys.exit(1)

    print("Running preprocessing...")
    df = run_pipeline(csv_path, missing_strategy="median", normalize=True)
    print(f"Preprocessed rows: {len(df)}, columns: {list(df.columns)}")

    print("Running training pipeline...")
    results = run_training_pipeline(
        csv_path,
        args.output_dir,
        missing_strategy="median",
        train_classification=True,
        train_forecasting=not args.no_lstm,
        train_anomaly_detection=True,
        lstm_seq_len=min(30, len(df) // 10),
        lstm_horizon=7,
        lstm_epochs=20,
    )

    print("\n--- Metrics ---")
    if results.get("metrics_classification"):
        m = results["metrics_classification"]
        print(f"Classification - Accuracy: {m['accuracy']:.4f}, F1 (weighted): {m['f1_weighted']:.4f}")
        print("Confusion matrix:", m["confusion_matrix"])
    if results.get("metrics_forecasting"):
        m = results["metrics_forecasting"]
        print(f"Forecasting - RMSE: {m['rmse']:.4f}, MAE: {m['mae']:.4f}")
    if results.get("metrics_anomaly"):
        m = results["metrics_anomaly"]
        print(f"Anomaly - n_anomalies: {m.get('n_anomalies', 'N/A')}")

    print("\nSaved models under:", args.output_dir)
    print("Done.")


if __name__ == "__main__":
    main()
