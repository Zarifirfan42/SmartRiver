"""
Full data pipeline: ingestion → cleaning → imputation → WQI → feature engineering.
"""
import os
from pathlib import Path
from typing import Optional, Literal

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from data_preprocessing.utils.wqi_calculator import (
    normalize_column_names,
    add_wqi_and_status,
    compute_wqi,
)


# Default column names expected in raw CSV (after normalization)
DATE_COL = "date"
STATION_COL = "station_code"
REQUIRED_PARAMS = ["DO", "BOD", "COD", "AN", "TSS", "pH"]


def ingest_csv(
    path: str | Path,
    date_column: Optional[str] = None,
    station_column: Optional[str] = None,
) -> pd.DataFrame:
    """
    Data ingestion: load CSV and normalize column names.
    """
    path = Path(path)
    if not path.suffix.lower() == ".csv":
        raise ValueError("File must be a CSV")
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_csv(path)
    df = normalize_column_names(df)

    # Normalize date column
    for c in ["date", "Date", "reading_date", "timestamp"]:
        if c in df.columns and date_column is None:
            date_column = c
    if date_column and date_column in df.columns:
        df[DATE_COL] = pd.to_datetime(df[date_column], errors="coerce")
    elif "date" not in df.columns and len(df.columns) > 0:
        df[DATE_COL] = pd.NaT

    # Station
    for c in ["station", "station_code", "Station", "location"]:
        if c in df.columns and station_column is None:
            station_column = c
    if station_column and station_column in df.columns:
        df[STATION_COL] = df[station_column].astype(str)
    elif STATION_COL not in df.columns:
        df[STATION_COL] = "S01"

    return df


def clean_data(
    df: pd.DataFrame,
    remove_duplicates: bool = True,
    duplicate_subset: Optional[list] = None,
) -> pd.DataFrame:
    """
    Data cleaning: drop duplicates, drop rows with invalid numeric ranges.
    """
    out = df.copy()

    # Ensure numeric for params
    for col in REQUIRED_PARAMS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if remove_duplicates:
        subset = duplicate_subset or ([STATION_COL, DATE_COL] if DATE_COL in out.columns and STATION_COL in out.columns else None)
        if subset and all(c in out.columns for c in subset):
            out = out.drop_duplicates(subset=subset, keep="first")
        else:
            out = out.drop_duplicates(keep="first")

    # Optional: drop rows where all params are null
    param_cols = [c for c in REQUIRED_PARAMS if c in out.columns]
    if param_cols:
        out = out.loc[out[param_cols].notna().any(axis=1)]

    return out


def impute_missing(
    df: pd.DataFrame,
    strategy: Literal["mean", "median", "drop"] = "median",
) -> pd.DataFrame:
    """
    Missing value imputation for DO, BOD, COD, AN, TSS, pH.
    strategy: 'mean', 'median', or 'drop' (drop rows with any missing in these cols).
    """
    from sklearn.impute import SimpleImputer

    out = df.copy()
    param_cols = [c for c in REQUIRED_PARAMS if c in out.columns]
    if not param_cols:
        return out

    if strategy == "drop":
        return out.dropna(subset=param_cols)

    imp = SimpleImputer(strategy=strategy)
    out[param_cols] = imp.fit_transform(out[param_cols])
    return out


def add_wqi(df: pd.DataFrame) -> pd.DataFrame:
    """Add WQI and river_status columns."""
    return add_wqi_and_status(df, wqi_column="WQI")


def feature_engineering(
    df: pd.DataFrame,
    rolling_window: int = 7,
    lag_days: list = (1, 7, 14),
    normalize: bool = True,
    scaler: Optional[MinMaxScaler] = None,
) -> tuple[pd.DataFrame, Optional[MinMaxScaler]]:
    """
    Feature engineering: rolling stats, lags, optional normalization.
    Returns (df_with_features, fitted_scaler).
    """
    out = df.copy()
    if DATE_COL in out.columns:
        out = out.sort_values([STATION_COL, DATE_COL]).reset_index(drop=True)

    group_col = STATION_COL if STATION_COL in out.columns else None

    # Rolling mean/std of WQI
    if "WQI" in out.columns and rolling_window:
        if group_col:
            out["wqi_rolling_mean"] = out.groupby(group_col)["WQI"].transform(
                lambda x: x.rolling(rolling_window, min_periods=1).mean()
            )
            out["wqi_rolling_std"] = out.groupby(group_col)["WQI"].transform(
                lambda x: x.rolling(rolling_window, min_periods=1).std()
            )
        else:
            out["wqi_rolling_mean"] = out["WQI"].rolling(rolling_window, min_periods=1).mean()
            out["wqi_rolling_std"] = out["WQI"].rolling(rolling_window, min_periods=1).std()
        out["wqi_rolling_std"] = out["wqi_rolling_std"].fillna(0)

    # Lag features
    if "WQI" in out.columns and lag_days:
        if group_col:
            for lag in lag_days:
                out[f"wqi_lag_{lag}"] = out.groupby(group_col)["WQI"].shift(lag)
        else:
            for lag in lag_days:
                out[f"wqi_lag_{lag}"] = out["WQI"].shift(lag)
        for lag in lag_days:
            out[f"wqi_lag_{lag}"] = out[f"wqi_lag_{lag}"].ffill().bfill().fillna(0)

    # Optional normalization of numeric features for ML
    feature_cols = [c for c in out.columns if c not in [DATE_COL, STATION_COL, "river_status"] and out[c].dtype in ["float64", "int64"]]
    if normalize and feature_cols:
        if scaler is None:
            scaler = MinMaxScaler(feature_range=(0, 1))
            out[feature_cols] = scaler.fit_transform(out[feature_cols].fillna(0))
        else:
            out[feature_cols] = scaler.transform(out[feature_cols].fillna(0))
        return out, scaler
    return out, scaler


def ingest_many_csv(paths: list[str | Path]) -> pd.DataFrame:
    """Load and concatenate multiple CSVs with the same ingest rules as ``ingest_csv``."""
    if not paths:
        raise ValueError("ingest_many_csv: no paths provided")
    frames = [ingest_csv(Path(p)) for p in paths]
    return pd.concat(frames, ignore_index=True)


def _pipeline_after_ingest(
    df: pd.DataFrame,
    missing_strategy: Literal["mean", "median", "drop"],
    remove_duplicates: bool,
    rolling_window: int,
    lag_days: tuple,
    normalize: bool,
) -> pd.DataFrame:
    df = clean_data(df, remove_duplicates=remove_duplicates)
    df = impute_missing(df, strategy=missing_strategy)
    df = add_wqi(df)
    df, _ = feature_engineering(df, rolling_window=rolling_window, lag_days=list(lag_days), normalize=normalize)
    return df


def run_pipeline_multi(
    input_paths: list[str | Path],
    output_path: Optional[str | Path] = None,
    missing_strategy: Literal["mean", "median", "drop"] = "median",
    remove_duplicates: bool = True,
    rolling_window: int = 7,
    lag_days: tuple = (1, 7, 14),
    normalize: bool = True,
) -> pd.DataFrame:
    """
    Full pipeline over several CSV files (e.g. ``datasets/by_river/**/*.csv``).
    Ingests each file, concatenates, then shared clean → impute → WQI → features.
    """
    df = ingest_many_csv(list(input_paths))
    df = _pipeline_after_ingest(
        df,
        missing_strategy=missing_strategy,
        remove_duplicates=remove_duplicates,
        rolling_window=rolling_window,
        lag_days=lag_days,
        normalize=normalize,
    )
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
    return df


def run_pipeline(
    input_path: str | Path,
    output_path: Optional[str | Path] = None,
    missing_strategy: Literal["mean", "median", "drop"] = "median",
    remove_duplicates: bool = True,
    rolling_window: int = 7,
    lag_days: tuple = (1, 7, 14),
    normalize: bool = True,
) -> pd.DataFrame:
    """
    Run full pipeline: ingest → clean → impute → WQI → feature engineering.
    Optionally saves result to output_path CSV.
    """
    df = ingest_csv(input_path)
    df = _pipeline_after_ingest(
        df,
        missing_strategy=missing_strategy,
        remove_duplicates=remove_duplicates,
        rolling_window=rolling_window,
        lag_days=lag_days,
        normalize=normalize,
    )

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

    return df
