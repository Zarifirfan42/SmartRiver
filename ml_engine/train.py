"""
Train SmartRiver ML models (Random Forest, LSTM, Isolation Forest).

Requirements (from project root):
- Input: `datasets/by_river/**/*.csv` (default when present) or a single CSV in `datasets/`
- Preprocessing: `data_preprocessing.services.pipeline.run_pipeline` / `run_pipeline_multi`
- Outputs:
  - Random Forest (river_status classifier) -> ml_models/random_forest/model.joblib
  - LSTM (WQI forecast)                   -> ml_models/lstm/model.keras
  - Isolation Forest                     -> ml_models/anomaly_detection/model.joblib
  - Metrics JSON                         -> ml_models/training_metrics.json

Reported metrics (examiner-friendly):
- Random Forest: accuracy, precision (weighted), recall (weighted), F1 (weighted/macro), confusion matrix
- LSTM: MSE, RMSE, MAE, R² on held-out sequence windows
- Isolation Forest: sample count, flagged anomaly count / rate (unsupervised)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
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


def _path_for_report(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(p.resolve())


def _dedupe_one_csv_per_river(paths: list[Path]) -> list[Path]:
    """
    Keep only one CSV per river filename (e.g. only one `Sungai Kulim.csv`).
    If duplicates exist across folders, keep the larger file.
    """
    by_river: dict[str, Path] = {}
    for p in paths:
        key = p.stem.strip().lower()
        if not key:
            key = p.name.strip().lower()
        current = by_river.get(key)
        if current is None:
            by_river[key] = p
            continue
        try:
            keep_new = p.stat().st_size > current.stat().st_size
        except OSError:
            keep_new = False
        if keep_new:
            by_river[key] = p
    return sorted(by_river.values())


def _collect_training_csv_paths(
    datasets_dir: Path,
    csv_filename: str | None,
    use_by_river: bool,
) -> list[Path]:
    """Return ordered list of CSV paths to feed the preprocessing pipeline."""
    datasets_dir = Path(datasets_dir)
    if csv_filename:
        p = (datasets_dir / csv_filename).with_suffix(".csv")
        if not p.is_file():
            raise FileNotFoundError(f"CSV not found: {p}")
        return [p.resolve()]

    by_river = datasets_dir / "by_river"
    if use_by_river and by_river.is_dir():
        paths = sorted(p.resolve() for p in by_river.rglob("*.csv") if p.is_file())
        if paths:
            return _dedupe_one_csv_per_river(paths)

    return [_find_default_csv(datasets_dir).resolve()]


def _print_metrics_summary(rf_metrics: dict, lstm_metrics: dict | None, an_metrics: dict) -> None:
    print("\n" + "=" * 60)
    print("TRAINING METRICS SUMMARY")
    print("=" * 60)
    print("\n[Random Forest - river_status classification]")
    print(f"  Accuracy            : {rf_metrics.get('accuracy', 0):.4f}")
    print(f"  Precision (weighted): {rf_metrics.get('precision_weighted', 0):.4f}")
    print(f"  Recall (weighted)   : {rf_metrics.get('recall_weighted', 0):.4f}")
    print(f"  F1 (weighted)       : {rf_metrics.get('f1_weighted', 0):.4f}")
    print(f"  F1 (macro)          : {rf_metrics.get('f1_macro', 0):.4f}")
    cv = rf_metrics.get("cross_validation") or {}
    if cv:
        k = cv.get("n_folds", 0)
        ke = cv.get("n_folds_evaluated", k)
        k_suffix = f"k={k}" if ke == k else f"k={k}, evaluated={ke}"
        print(
            f"  CV accuracy (mean±std): {cv.get('mean_accuracy', 0):.4f} ± {cv.get('std_accuracy', 0):.4f}"
            f"  ({k_suffix})"
        )
    feat = rf_metrics.get("feature_columns") or []
    if feat:
        print(f"  Features used       : {feat}")
    if lstm_metrics:
        print("\n[LSTM - WQI multi-step forecast, held-out windows]")
        print(f"  MSE : {lstm_metrics.get('mse', 0):.4f}")
        print(f"  RMSE: {lstm_metrics.get('rmse', 0):.4f}")
        print(f"  MAE : {lstm_metrics.get('mae', 0):.4f}")
        print(f"  R²  : {lstm_metrics.get('r2', 0):.4f}")
        baseline = lstm_metrics.get("baseline") or {}
        improve = lstm_metrics.get("improvement_vs_baseline_pct") or {}
        if baseline:
            print(
                f"  Baseline (prev-step) RMSE/MAE: {baseline.get('rmse', 0):.4f} / {baseline.get('mae', 0):.4f}"
            )
            print(
                f"  Improvement vs baseline (%): RMSE {improve.get('rmse', 0):.2f}% | MAE {improve.get('mae', 0):.2f}%"
            )
    else:
        print("\n[LSTM - skipped (see message above)]")
    print("\n[Isolation Forest - anomaly detection (unsupervised)]")
    print(f"  Training rows       : {an_metrics.get('n_samples', 0)}")
    print(f"  Flagged anomalies   : {an_metrics.get('n_flagged_anomalies', 0)}")
    print(f"  Anomaly rate        : {an_metrics.get('anomaly_rate', 0):.4f}")
    print("=" * 60 + "\n")


def run_training_from_paths(
    paths: list[Path],
    *,
    missing_strategy: str = "median",
    normalize: bool = True,
    lstm_seq_len: int = 30,
    lstm_horizon: int = 7,
    lstm_epochs: int = 50,
    lstm_station: str | None = None,
    lstm_verbose: int = 1,
    write_metrics_json: bool = True,
    metrics_json: Path | None = None,
    print_summary: bool = True,
) -> dict:
    """
    Train RF + LSTM + Isolation Forest from one or more CSV paths (after SmartRiver pipeline).
    Returns a JSON-serializable metrics dict (also written to ml_models/training_metrics.json when enabled).
    """
    from data_preprocessing.services.pipeline import (
        ingest_csv,
        ingest_many_csv,
        clean_data,
        impute_missing,
        add_wqi,
        feature_engineering,
    )
    from ml_engine.services.classification_service import train as train_rf, save_model as save_rf
    from ml_engine.services.forecasting_service import train as train_lstm
    from ml_engine.services.anomaly_service import train as train_anom, save_model as save_anom

    paths = [Path(p).resolve() for p in paths]
    if len(paths) == 1:
        print(f"Loading CSV: {paths[0]}")
        df_raw = ingest_csv(paths[0])
    else:
        print(f"Loading {len(paths)} CSV files:")
        for p in paths[:12]:
            print(f"  - {_path_for_report(p)}")
        if len(paths) > 12:
            print(f"  ... and {len(paths) - 12} more")
        df_raw = ingest_many_csv(paths)

    # Shared, leakage-safe base table: clean + impute + WQI/river_status only.
    df_base = clean_data(df_raw, remove_duplicates=True)
    df_base = impute_missing(df_base, strategy=missing_strategy)
    df_base = add_wqi(df_base)
    print(f"Base frame shape (pre-feature-engineering): {df_base.shape}")

    # Feature engineering/scaling are built AFTER base table and used for non-RF tasks.
    df, _ = feature_engineering(
        df_base,
        rolling_window=7,
        lag_days=[1, 7, 14],
        normalize=normalize,
    )
    print(f"Engineered frame shape: {df.shape}")

    out_root = PROJECT_ROOT / "ml_models"
    out_root.mkdir(parents=True, exist_ok=True)

    metrics_out: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_csvs": [_path_for_report(p) for p in paths],
        "preprocessed_rows": int(len(df)),
        "random_forest_classification": {},
        "lstm_regression": {},
        "isolation_forest": {},
    }

    rf_out = train_rf(df_base)
    rf_path = out_root / "random_forest" / "model.joblib"
    save_rf(rf_out["model"], rf_out["feature_columns"], rf_path)
    print(f"Saved Random Forest: {rf_path}")
    print(f"Random Forest final feature list: {rf_out['feature_columns']}")
    rf_m = rf_out.get("metrics") or {}
    metrics_out["random_forest_classification"] = {
        "accuracy": rf_m.get("accuracy"),
        "precision_weighted": rf_m.get("precision_weighted"),
        "recall_weighted": rf_m.get("recall_weighted"),
        "f1_weighted": rf_m.get("f1_weighted"),
        "f1_macro": rf_m.get("f1_macro"),
        "labels": rf_m.get("labels"),
        "confusion_matrix": rf_m.get("confusion_matrix"),
        "classification_report": rf_m.get("classification_report"),
        "cross_validation": rf_m.get("cross_validation"),
        "split_info": rf_m.get("split_info"),
        "feature_columns": rf_out.get("feature_columns"),
    }

    lstm_dir = out_root / "lstm"
    lstm_dir.mkdir(parents=True, exist_ok=True)
    lstm_out = train_lstm(
        df,
        station_code=lstm_station,
        seq_len=lstm_seq_len,
        horizon=lstm_horizon,
        epochs=lstm_epochs,
        verbose=lstm_verbose,
    )
    lstm_metrics = None
    if lstm_out.get("error"):
        print(f"Skipped LSTM: {lstm_out['error']}")
        metrics_out["lstm_regression"] = {"error": lstm_out["error"]}
    else:
        lstm_metrics = lstm_out.get("metrics") or {}
        metrics_out["lstm_regression"] = {
            **lstm_metrics,
            "final_train_loss": (lstm_out.get("train_loss") or [])[-1:] if lstm_out.get("train_loss") else None,
            "final_val_loss": (lstm_out.get("val_loss") or [])[-1:] if lstm_out.get("val_loss") else None,
            "seq_len": lstm_seq_len,
            "horizon": lstm_horizon,
        }
        model_file = lstm_dir / "model.keras"
        lstm_out["model"].save(model_file)
        import joblib

        joblib.dump(
            {"scaler": lstm_out.get("scaler"), "config": {"seq_len": lstm_seq_len, "horizon": lstm_horizon}},
            lstm_dir / "scaler.joblib",
        )
        print(f"Saved LSTM: {model_file}")

    an_out = train_anom(df)
    an_path = out_root / "anomaly_detection" / "model.joblib"
    save_anom(an_out["model"], an_out["feature_columns"], an_path)
    print(f"Saved Isolation Forest: {an_path}")
    pred = an_out.get("predictions")
    n_flagged = int((pred == -1).sum()) if pred is not None else 0
    n_samples = len(df)
    metrics_out["isolation_forest"] = {
        "n_samples": n_samples,
        "n_flagged_anomalies": n_flagged,
        "anomaly_rate": round(n_flagged / n_samples, 6) if n_samples else 0.0,
        "feature_columns": an_out.get("feature_columns"),
    }

    if write_metrics_json:
        mpath = metrics_json or (out_root / "training_metrics.json")
        mpath.parent.mkdir(parents=True, exist_ok=True)
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(metrics_out, f, indent=2)
        print(f"Wrote metrics: {mpath}")

    if print_summary:
        _print_metrics_summary(rf_m, lstm_metrics, metrics_out["isolation_forest"])
    return metrics_out


def main() -> int:
    parser = argparse.ArgumentParser(description="Train SmartRiver models from DOE Malaysia CSV in datasets/.")
    parser.add_argument("--datasets-dir", type=Path, default=PROJECT_ROOT / "datasets", help="Datasets directory (default: ./datasets)")
    parser.add_argument("--csv", type=str, default=None, help="Single CSV filename inside datasets-dir (overrides by-river bundle)")
    parser.add_argument(
        "--no-by-river",
        action="store_true",
        help="Do not merge datasets/by_river/**/*.csv; use a single root CSV only.",
    )
    parser.add_argument("--missing-strategy", choices=["mean", "median", "drop"], default="median")
    parser.add_argument("--no-normalize", action="store_true", help="Disable feature normalization in preprocessing")
    parser.add_argument("--lstm-seq-len", type=int, default=30)
    parser.add_argument("--lstm-horizon", type=int, default=7)
    parser.add_argument("--lstm-epochs", type=int, default=50)
    parser.add_argument("--lstm-station", type=str, default=None, help="Optional station_code to train LSTM on")
    parser.add_argument(
        "--metrics-json",
        type=Path,
        default=None,
        help="Where to write training_metrics.json (default: ml_models/training_metrics.json)",
    )
    args = parser.parse_args()

    paths = _collect_training_csv_paths(
        Path(args.datasets_dir),
        args.csv,
        use_by_river=not args.no_by_river,
    )

    run_training_from_paths(
        paths,
        missing_strategy=args.missing_strategy,
        normalize=not args.no_normalize,
        lstm_seq_len=args.lstm_seq_len,
        lstm_horizon=args.lstm_horizon,
        lstm_epochs=args.lstm_epochs,
        lstm_station=args.lstm_station,
        lstm_verbose=1,
        write_metrics_json=True,
        metrics_json=args.metrics_json,
        print_summary=True,
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

