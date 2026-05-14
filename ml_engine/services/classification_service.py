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
from sklearn.model_selection import (
    train_test_split,
    GroupShuffleSplit,
    StratifiedKFold,
    StratifiedGroupKFold,
)
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
SAFE_RAW_FEATURES = ["DO", "BOD", "COD", "AN", "TSS", "pH"]
LEAKY_NAME_TOKENS = (
    "status",
    "label",
    "class",
    "target",
    "wqi",
    "lag",
    "rolling",
    "anomaly",
    "forecast",
    "predict",
)


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """
    Leakage-safe feature selector for river_status classification.
    Priority: only raw water-quality parameters.
    Fallback: numeric columns excluding any names that indicate target-derived information.
    """
    raw = [c for c in SAFE_RAW_FEATURES if c in df.columns]
    if raw:
        return raw

    exclude = {"river_status", "date", "station_code", "station", "station_name", "river_name"}
    safe_cols: list[str] = []
    for c in df.columns:
        c_low = c.lower()
        if c in exclude:
            continue
        if any(tok in c_low for tok in LEAKY_NAME_TOKENS):
            continue
        if df[c].dtype in (np.float64, np.int64, "float64", "int64"):
            safe_cols.append(c)
    return safe_cols


def _group_key_column(df: pd.DataFrame) -> Optional[str]:
    """Prefer station grouping to prevent leakage between train and test."""
    for c in ("station_code", "station_name", "river_name"):
        if c in df.columns:
            return c
    return None


def _build_group_labels(df: pd.DataFrame) -> Optional[pd.Series]:
    col = _group_key_column(df)
    if not col:
        return None
    s = df[col].astype(str).fillna("").str.strip()
    if s.nunique(dropna=True) <= 1:
        return None
    return s


def _group_aware_split_indices(
    y_enc: np.ndarray,
    groups: Optional[pd.Series],
    test_size: float,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Split indices for train/test.
    - If groups available: keep group disjoint via GroupShuffleSplit (no station leakage).
    - Else: stratified random split.
    """
    idx = np.arange(len(y_enc))
    if groups is not None:
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        train_idx, test_idx = next(gss.split(idx, y_enc, groups=groups))
        return train_idx, test_idx
    train_idx, test_idx = train_test_split(
        idx, test_size=test_size, random_state=random_state, stratify=y_enc
    )
    return np.asarray(train_idx), np.asarray(test_idx)


def _cross_validate_accuracy(
    X: pd.DataFrame,
    y_enc: np.ndarray,
    groups: Optional[pd.Series],
    *,
    n_estimators: int,
    max_depth: int,
    min_samples_leaf: int,
    random_state: int,
    folds: int = 5,
) -> dict[str, Any]:
    """
    Cross-validation for RF classification.
    - No groups: StratifiedKFold (shuffled), n_splits = min(requested, min class count, 2..).
    - With groups: StratifiedGroupKFold so the same station/river never appears in both train and
      test within a fold. n_splits MUST NOT exceed the number of unique groups, otherwise sklearn
      emits empty test folds (invalid).
    """
    n_samples = len(y_enc)
    if n_samples < 2:
        return {
            "fold_accuracy": [],
            "mean_accuracy": 0.0,
            "std_accuracy": 0.0,
            "n_folds": 0,
            "n_folds_evaluated": 0,
            "note": "insufficient samples for cross-validation",
        }

    class_counts = pd.Series(y_enc).value_counts()
    min_class_count = int(class_counts.min()) if len(class_counts) else 0
    n_groups = int(groups.astype(str).nunique(dropna=False)) if groups is not None else 0

    if groups is not None and n_groups >= 2:
        # Critical: StratifiedGroupKFold(n_splits=k) requires k <= n_unique_groups or some folds are empty.
        n_splits = min(folds, n_groups)
        if min_class_count >= 2:
            n_splits = min(n_splits, min_class_count)
        n_splits = max(2, n_splits)
        n_splits = min(n_splits, n_groups)
        cv_splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        split_iter = cv_splitter.split(X, y_enc, groups=groups)
    else:
        n_splits = min(folds, min_class_count) if min_class_count >= 2 else 2
        n_splits = max(2, min(n_splits, n_samples))
        cv_splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        split_iter = cv_splitter.split(X, y_enc)

    scores: list[float] = []
    for tr, te in split_iter:
        if len(tr) == 0 or len(te) == 0:
            continue
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            class_weight="balanced",
            random_state=random_state,
        )
        model.fit(X.iloc[tr], y_enc[tr])
        pred = model.predict(X.iloc[te])
        scores.append(float(accuracy_score(y_enc[te], pred)))

    return {
        "fold_accuracy": scores,
        "mean_accuracy": float(np.mean(scores)) if scores else 0.0,
        "std_accuracy": float(np.std(scores)) if len(scores) > 1 else 0.0,
        "n_folds": int(n_splits),
        "n_folds_evaluated": int(len(scores)),
        "n_unique_groups": n_groups if groups is not None else None,
    }


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

    groups = _build_group_labels(df.loc[valid].reset_index(drop=True) if not valid.all() else df.reset_index(drop=True))
    train_idx, test_idx = _group_aware_split_indices(
        y_enc=y_enc,
        groups=groups,
        test_size=test_size,
        random_state=random_state,
    )
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y_enc[train_idx], y_enc[test_idx]

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

    cv = _cross_validate_accuracy(
        X=X,
        y_enc=y_enc,
        groups=groups,
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
        folds=5,
    )

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
        "cross_validation": cv,
        "split_info": {
            "test_size": float(test_size),
            "train_rows": int(len(train_idx)),
            "test_rows": int(len(test_idx)),
            "group_column": _group_key_column(df) if groups is not None else None,
            "group_disjoint": bool(groups is not None),
        },
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
