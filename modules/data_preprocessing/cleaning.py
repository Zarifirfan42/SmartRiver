"""
Cleaning — Data cleaning and missing value imputation.
Part of the preprocessing pipeline before WQI and feature engineering.
"""
from typing import Literal
import pandas as pd
from sklearn.impute import SimpleImputer


def remove_duplicates(
    df: pd.DataFrame,
    subset: list | None = None,
) -> pd.DataFrame:
    """Drop duplicate rows. Default: by station_code and date if present."""
    if subset is None:
        subset = [c for c in ["station_code", "date"] if c in df.columns]
    if subset:
        return df.drop_duplicates(subset=subset, keep="first")
    return df.drop_duplicates(keep="first")


def impute_missing(
    df: pd.DataFrame,
    strategy: Literal["mean", "median", "drop"] = "median",
    columns: list | None = None,
) -> pd.DataFrame:
    """
    Impute missing values in numeric columns.
    strategy: 'mean', 'median', or 'drop' (drop rows with any missing in columns).
    """
    param_cols = columns or [c for c in ["DO", "BOD", "COD", "AN", "TSS", "pH"] if c in df.columns]
    if not param_cols:
        return df
    if strategy == "drop":
        return df.dropna(subset=param_cols)
    imp = SimpleImputer(strategy=strategy)
    out = df.copy()
    out[param_cols] = imp.fit_transform(out[param_cols])
    return out


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Full cleaning: coerce numerics, remove duplicates, optional imputation."""
    out = df.copy()
    for c in ["DO", "BOD", "COD", "AN", "TSS", "pH"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = remove_duplicates(out)
    out = impute_missing(out, strategy="median")
    return out
