"""
Random Forest classifier for river status: Clean / Slightly Polluted / Polluted.
Training, evaluation (Accuracy, F1, confusion matrix), and prediction.
"""
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    confusion_matrix,
    classification_report,
    precision_score,
    recall_score,
)


RIVER_STATUS_ORDER = ["clean", "slightly_polluted", "polluted"]
RANDOM_STATE = 42


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Numeric columns suitable as features (exclude target and ids)."""
    exclude = {"river_status", "date", "station_code", "station"}
    return [c for c in df.columns if c != "river_status" and df[c].dtype in (np.float64, np.int64, "float64", "int64") and c not in exclude]


def train(
    df: pd.DataFrame,
    target_column: str = "river_status",
    test_size: float = 0.2,
    n_estimators: int = 150,
    max_depth: int = 15,
    min_samples_leaf: int = 5,
    random_state: int = RANDOM_STATE,
) -> dict[str, Any]:
    """
    Train Random Forest classifier. Expects df with WQI/features and river_status.
    Returns metrics and the trained model.
    """
    feature_cols = get_feature_columns(df)
    if not feature_cols:
        feature_cols = [c for c in ["WQI", "DO", "BOD", "COD", "AN", "TSS", "pH"] if c in df.columns]
    if not feature_cols:
        raise ValueError("No feature columns found")

    X = df[feature_cols].fillna(0)
    y = df[target_column].astype(str).str.lower().str.replace(" ", "_")
    valid = y.isin(RIVER_STATUS_ORDER)
    if not valid.all():
        n_bad = int((~valid).sum())
        # Typical cause: NaN WQI → "unknown" from wqi_to_status after merging CSVs.
        X = X.loc[valid].reset_index(drop=True)
        y = y.loc[valid].reset_index(drop=True)
        if len(y) == 0:
            raise ValueError(
                "No rows with river_status in {clean, slightly_polluted, polluted}. "
                "Check WQI/parameter columns after preprocessing."
            )
        import warnings
        warnings.warn(
            f"Dropped {n_bad} row(s) with invalid river_status (e.g. unknown); training on {len(y)} rows.",
            UserWarning,
            stacklevel=2,
        )
    y_enc = pd.Categorical(y, categories=RIVER_STATUS_ORDER).codes

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=test_size, random_state=random_state, stratify=y_enc
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        class_weight="balanced",
        random_state=random_state,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1_weighted = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    precision_w = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall_w = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])

    metrics = {
        "accuracy": float(accuracy),
        "f1_weighted": float(f1_weighted),
        "f1_macro": float(f1_macro),
        "precision_weighted": float(precision_w),
        "recall_weighted": float(recall_w),
        "confusion_matrix": cm.tolist(),
        "labels": RIVER_STATUS_ORDER,
        "classification_report": classification_report(
            y_test,
            y_pred,
            labels=[0, 1, 2],
            target_names=RIVER_STATUS_ORDER,
            zero_division=0,
            output_dict=True,
        ),
    }

    return {
        "model": model,
        "feature_columns": feature_cols,
        "metrics": metrics,
        "classes": RIVER_STATUS_ORDER,
    }


def evaluate(model: Any, X: pd.DataFrame, y_true: pd.Series) -> dict[str, Any]:
    """Compute accuracy, F1, confusion matrix on given data."""
    classes = list(pd.Categorical(y_true).categories)
    y_enc = pd.Categorical(y_true.astype(str).str.lower().str.replace(" ", "_"), categories=RIVER_STATUS_ORDER).codes
    y_pred = model.predict(X.fillna(0))
    return {
        "accuracy": float(accuracy_score(y_enc, y_pred)),
        "f1_weighted": float(f1_score(y_enc, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_enc, y_pred, labels=[0, 1, 2]).tolist(),
        "labels": RIVER_STATUS_ORDER,
    }


def predict(
    model: Any,
    df: pd.DataFrame,
    feature_columns: Optional[list[str]] = None,
) -> np.ndarray:
    """Predict river status codes (0=clean, 1=slightly_polluted, 2=polluted)."""
    if feature_columns is None:
        feature_columns = get_feature_columns(df)
    if not feature_columns:
        feature_columns = [c for c in ["WQI", "DO", "BOD", "COD", "AN", "TSS", "pH"] if c in df.columns]
    X = df[feature_columns].fillna(0)
    return model.predict(X)


def predict_labels(
    model: Any,
    df: pd.DataFrame,
    feature_columns: Optional[list[str]] = None,
) -> list[str]:
    """Predict river status labels."""
    codes = predict(model, df, feature_columns)
    return [RIVER_STATUS_ORDER[int(c)] for c in codes]


def save_model(model: Any, feature_columns: list[str], path: str | Path) -> None:
    """Save model and metadata with joblib."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "feature_columns": feature_columns, "classes": RIVER_STATUS_ORDER},
        path,
    )


def load_model(path: str | Path) -> tuple[Any, list[str]]:
    """Load model and feature columns."""
    data = joblib.load(path)
    return data["model"], data.get("feature_columns", [])
