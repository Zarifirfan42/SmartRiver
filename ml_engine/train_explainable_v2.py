"""
SmartRiver explainable ML retraining script (FYP-friendly).

What this script does:
1) Loads existing model.joblib and explains model type + expected features
2) Builds a clear end-to-end training pipeline
3) Evaluates with RMSE / MAE / R2
4) Shows one actual vs predicted example
5) Saves improved model artifact as model_v2.joblib

This script is additive and does not modify existing pipelines.
"""
from __future__ import annotations

from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# Reuse your existing preprocessing function so project behavior stays consistent.
from data_preprocessing.services.pipeline import run_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXISTING_MODEL_PATH = PROJECT_ROOT / "ml_models" / "random_forest" / "model.joblib"
OUTPUT_MODEL_PATH = PROJECT_ROOT / "ml_models" / "random_forest" / "model_v2.joblib"
DEFAULT_DATASET = PROJECT_ROOT / "datasets" / "sample_water_quality.csv"


def load_and_explain_existing_model(path: Path) -> dict:
    """
    Load existing model artifact and print explainable summary.
    """
    print("\n=== 1) Existing Model Inspection ===")
    if not path.exists():
        print(f"Existing model not found at: {path}")
        return {"model": None, "feature_columns": []}

    obj = joblib.load(path)
    model = obj["model"] if isinstance(obj, dict) and "model" in obj else obj
    feature_columns = obj.get("feature_columns", []) if isinstance(obj, dict) else []

    print(f"Model file: {path}")
    print(f"Model type: {type(model).__name__}")
    print(f"Expected input features ({len(feature_columns)}): {feature_columns}")

    # Simple explanation for examiners.
    print(
        "How it works (simple): Random Forest combines many decision trees. "
        "Each tree makes a prediction, then the forest averages the results "
        "(for regression) or votes (for classification)."
    )
    return {"model": model, "feature_columns": feature_columns}


def build_training_dataframe(dataset_path: Path) -> pd.DataFrame:
    """
    Load dataset through existing preprocessing pipeline and print structure.
    """
    print("\n=== 2) Data Loading and Preparation ===")
    df = run_pipeline(
        dataset_path,
        output_path=None,
        missing_strategy="median",
        remove_duplicates=True,
        rolling_window=7,
        lag_days=(1, 7, 14),
        normalize=False,  # keep original scale for explainability
    )

    print(f"Dataset path: {dataset_path}")
    print(f"Rows: {len(df)} | Columns: {len(df.columns)}")
    print("Columns:", list(df.columns))
    print("\nSample rows:")
    print(df.head(3).to_string(index=False))

    missing = df.isna().sum()
    print("\nMissing values (top columns):")
    print(missing[missing > 0].sort_values(ascending=False).head(10).to_string() or "No missing values")
    return df


def train_explainable_model(df: pd.DataFrame):
    """
    Train a professional, readable regression pipeline for WQI prediction.
    """
    print("\n=== 3) Training Pipeline (80/20 split) ===")

    # Clear target definition for exam presentation.
    target_col = "WQI"
    if target_col not in df.columns:
        raise ValueError("Target column 'WQI' not found after preprocessing")

    # Select simple, interpretable features.
    numeric_features = [c for c in ["DO", "BOD", "COD", "AN", "TSS", "pH"] if c in df.columns]
    categorical_features = [c for c in ["station_code"] if c in df.columns]
    feature_columns = numeric_features + categorical_features
    if not feature_columns:
        raise ValueError("No valid feature columns found")

    print(f"Target: {target_col}")
    print(f"Numeric features: {numeric_features}")
    print(f"Categorical features: {categorical_features}")

    X = df[feature_columns].copy()
    y = df[target_col].astype(float).copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"Train size: {len(X_train)} | Test size: {len(X_test)}")

    # Missing value handling is explicit and reproducible.
    numeric_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ],
        remainder="drop",
    )

    model = RandomForestRegressor(
        n_estimators=250,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    return pipeline, feature_columns, X_test, y_test, y_pred


def evaluate_model(y_test: pd.Series, y_pred: np.ndarray) -> dict:
    """
    Evaluate model with RMSE, MAE, R2 and print explanation.
    """
    print("\n=== 4) Model Evaluation ===")
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    print(f"RMSE: {rmse:.4f}")
    print(f"MAE : {mae:.4f}")
    print(f"R2  : {r2:.4f}")

    print("\nMetric meaning:")
    print("- RMSE: average prediction error with stronger penalty for large errors (lower is better).")
    print("- MAE : average absolute error in WQI points (easy to interpret, lower is better).")
    print("- R2  : how much variance is explained by the model (closer to 1 is better).")

    if rmse < 5 and mae < 4:
        verdict = "Good for practical WQI estimation on this dataset."
    elif rmse < 10 and mae < 8:
        verdict = "Moderate; usable but can be improved with more data/features."
    else:
        verdict = "Needs improvement; consider data quality and feature engineering."
    print(f"Verdict: {verdict}")
    return {"rmse": rmse, "mae": mae, "r2": r2, "verdict": verdict}


def show_prediction_example(X_test: pd.DataFrame, y_test: pd.Series, y_pred: np.ndarray) -> None:
    """
    Show one sample: actual vs predicted value.
    """
    print("\n=== 5) Prediction Example ===")
    idx = y_test.index[0]
    actual = float(y_test.iloc[0])
    predicted = float(y_pred[0])
    row = X_test.iloc[0].to_dict()

    print("Input sample features:")
    print(row)
    print(f"Actual WQI   : {actual:.3f}")
    print(f"Predicted WQI: {predicted:.3f}")
    print(f"Absolute diff: {abs(actual - predicted):.3f}")


def save_model_v2(pipeline: Pipeline, feature_columns: list[str], metrics: dict, out_path: Path) -> None:
    """
    Save improved model and metadata as model_v2.joblib.
    """
    print("\n=== 6) Save Improved Model ===")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": pipeline,
        "feature_columns": feature_columns,
        "target": "WQI",
        "algorithm": "RandomForestRegressor",
        "metrics": metrics,
    }
    joblib.dump(payload, out_path)
    print(f"Saved: {out_path}")

    # Optional metadata file for quick README/table references.
    meta_path = out_path.with_suffix(".json")
    meta = {
        "model_path": str(out_path),
        "algorithm": "RandomForestRegressor",
        "feature_columns": feature_columns,
        "target": "WQI",
        "metrics": metrics,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved metadata: {meta_path}")


def print_fyp_explanation() -> None:
    """
    FYP-oriented summary for presentation.
    """
    print("\n=== 7) FYP Explanation ===")
    print("Why this model was chosen:")
    print("- Random Forest is robust on tabular environmental data and easy to explain.")
    print("- It handles non-linear relationships between water parameters and WQI.")

    print("\nHow it helps predict water quality:")
    print("- It learns historical relationships from DO, BOD, COD, AN, TSS, pH, and station context.")
    print("- It predicts expected WQI for decision support and early monitoring.")

    print("\nLimitations:")
    print("- Performance depends on data quality and representativeness.")
    print("- Sudden unseen pollution events may still cause prediction error.")
    print("- Retraining is needed when new patterns or stations are introduced.")


def main() -> int:
    print("SmartRiver Explainable ML Pipeline (v2)")
    print("======================================")

    load_and_explain_existing_model(EXISTING_MODEL_PATH)
    df = build_training_dataframe(DEFAULT_DATASET)
    pipeline, feature_columns, X_test, y_test, y_pred = train_explainable_model(df)
    metrics = evaluate_model(y_test, y_pred)
    show_prediction_example(X_test, y_test, y_pred)
    save_model_v2(pipeline, feature_columns, metrics, OUTPUT_MODEL_PATH)
    print_fyp_explanation()

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

