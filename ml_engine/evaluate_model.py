"""
SmartRiver — evaluate_model.py
==============================

Evaluate a saved joblib model against a CSV dataset.

IMPORTANT (FYP note):
- ml_models/random_forest/model.joblib is a **classification** bundle:
  { "model", "feature_columns", "classes" } → RandomForestClassifier for river_status.
  Use **accuracy / F1**, not RMSE/MAE on class names.

- ml_models/random_forest/model_v2.joblib is a **regression** pipeline for **WQI**:
  Use **RMSE / MAE / R²**.

Usage (from project root, with PYTHONPATH set):
  .venv\\Scripts\\python.exe ml_engine/evaluate_model.py --model ml_models/random_forest/model_v2.joblib
  .venv\\Scripts\\python.exe ml_engine/evaluate_model.py --model ml_models/random_forest/model.joblib

If your CSV has no WQI / river_status yet, pass --preprocess (or the script auto-runs the pipeline when those columns are missing).

See also: ml_engine/train_explainable_v2.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import is_classifier, is_regressor
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Same preprocessing as training for raw CSVs like sample_water_quality.csv
try:
    from data_preprocessing.services.pipeline import run_pipeline
except ImportError:
    run_pipeline = None


def _load_artifact(path: Path):
    obj = joblib.load(path)
    if isinstance(obj, dict) and "model" in obj:
        return obj["model"], obj.get("feature_columns", []), obj.get("classes"), obj.get("target")
    return obj, [], None, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SmartRiver model.joblib or model_v2.joblib")
    parser.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "ml_models" / "random_forest" / "model_v2.joblib",
        help="Path to joblib file",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=PROJECT_ROOT / "datasets" / "sample_water_quality.csv",
        help="Path to CSV (raw or preprocessed)",
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Run full SmartRiver pipeline on CSV (recommended for raw sample_water_quality.csv)",
    )
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    if not args.model.exists():
        raise FileNotFoundError(f"Model not found: {args.model}")
    if not args.csv.exists():
        raise FileNotFoundError(f"CSV not found: {args.csv}")

    model, feature_columns, classes, target_from_meta = _load_artifact(args.model)
    use_normalize = bool(is_classifier(model))
    if hasattr(model, "named_steps") and "preprocessor" in getattr(model, "named_steps", {}):
        use_normalize = False

    # --- 1) Load dataset (match training: RF classifier uses normalize=True in ml_engine/train.py) ---
    df = pd.read_csv(args.csv)
    needs_targets = "WQI" not in df.columns and "river_status" not in df.columns
    if (args.preprocess or needs_targets) and run_pipeline is not None:
        df = run_pipeline(
            args.csv,
            output_path=None,
            missing_strategy="median",
            remove_duplicates=True,
            rolling_window=7,
            lag_days=(1, 7, 14),
            normalize=use_normalize,
        )
    elif needs_targets and run_pipeline is None:
        raise RuntimeError(
            "CSV has no WQI/river_status and preprocessing could not be imported. "
            "Run from the project folder (SmartRiver root)."
        )

    print("Dataset preview:")
    print(df.head())
    print(f"\nShape: {df.shape}")

    # --- 2) Decide task + build X, y ---
    if isinstance(model, dict):
        raise TypeError("Unexpected: joblib root is a dict without 'model' key. Check file.")

    # Pipeline (model_v2): expects columns like DO, BOD, ..., station_code; target WQI
    if hasattr(model, "named_steps") and "preprocessor" in getattr(model, "named_steps", {}):
        target_col = target_from_meta or "WQI"
        if target_col not in df.columns:
            raise ValueError(f"Target '{target_col}' missing. Use --preprocess or a preprocessed CSV.")
        # Infer feature columns from the first step if possible
        if feature_columns:
            feats = feature_columns
        else:
            num = [c for c in ["DO", "BOD", "COD", "AN", "TSS", "pH"] if c in df.columns]
            cat = [c for c in ["station_code"] if c in df.columns]
            feats = num + cat
        X = df[feats].copy()
        y_reg = df[target_col].astype(float)
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_reg, test_size=args.test_size, random_state=args.random_state
        )
        y_pred = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae = float(mean_absolute_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))
        print("\n=== MODEL EVALUATION (Regression: WQI) ===")
        print(f"RMSE: {rmse:.4f}")
        print(f"MAE : {mae:.4f}")
        print(f"R2  : {r2:.4f}")
        print("\nRMSE = root mean squared error in WQI units (large errors penalised more).")
        print("MAE  = mean absolute error in WQI points (easy to explain).")
        comp = pd.DataFrame({"Actual": y_test.values, "Predicted": y_pred}).reset_index(drop=True)
        print("\nSample predictions:")
        print(comp.head(10))
        return 0

    # Standalone regressor/classifier or dict-loaded sklearn estimator
    if is_regressor(model):
        target_col = target_from_meta or "WQI"
        if target_col not in df.columns:
            raise ValueError("Regression model needs target column in dataframe (e.g. WQI). Use --preprocess.")
        if not feature_columns:
            feature_columns = [c for c in df.columns if c != target_col and df[c].dtype in ["float64", "int64"]]
        X = df[feature_columns].fillna(0)
        y = df[target_col].astype(float)
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, random_state=args.random_state
        )
        y_pred = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae = float(mean_absolute_error(y_test, y_pred))
        print("\n=== MODEL EVALUATION (Regression) ===")
        print(f"RMSE: {rmse:.4f}")
        print(f"MAE : {mae:.4f}")
        comp = pd.DataFrame({"Actual": y_test.values, "Predicted": y_pred})
        print(comp.head())
        return 0

    if is_classifier(model):
        # Classification: river_status
        target_col = "river_status"
        if target_col not in df.columns:
            raise ValueError(
                f"Classifier needs '{target_col}'. Use --preprocess with raw DOE-style CSV, "
                "or load a CSV that already has river_status."
            )
        if not feature_columns:
            raise ValueError("No feature_columns in artifact; cannot evaluate classifier.")
        X = df[feature_columns].fillna(0)
        y = df[target_col].astype(str).str.lower().str.replace(" ", "_")
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, random_state=args.random_state, stratify=y
        )
        y_pred_codes = model.predict(X_test)
        # Map codes to labels if needed
        if classes is not None and len(classes):
            pred_labels = [classes[int(i)] for i in y_pred_codes]
        else:
            pred_labels = y_pred_codes
        acc = accuracy_score(y_test, pred_labels)
        f1 = f1_score(y_test, pred_labels, average="weighted", zero_division=0)
        print("\n=== MODEL EVALUATION (Classification: river_status) ===")
        print(f"Accuracy: {acc:.4f}")
        print(f"F1 (weighted): {f1:.4f}")
        print(
            "\nFor classification, RMSE/MAE on class names are not standard. "
            "Use accuracy and F1 for examiner-friendly reporting."
        )
        comp = pd.DataFrame({"Actual": y_test.values, "Predicted": pred_labels})
        print("\nSample predictions:")
        print(comp.head(10))
        return 0

    # Fallback: try regression metrics
    print("Unknown estimator type; attempting regression-style predict.")
    if not feature_columns or "WQI" not in df.columns:
        print("Provide a regression model or use model_v2.joblib with --preprocess.")
        return 1
    X = df[feature_columns].fillna(0)
    y = df["WQI"].astype(float)
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state
    )
    y_pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mae = float(mean_absolute_error(y_test, y_pred))
    print(f"\nRMSE: {rmse:.4f}\nMAE : {mae:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
