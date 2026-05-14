"""
Preprocess dataset — Load CSV from /datasets, clean, impute, select features,
compute and normalize WQI, then train-test split.

Target schema (after `load_dataset`), for exporter / examiner alignment:
- **date** — parsed datetime (from `date`, `SMP-DAT`, `Tarikh`, …)
- **station_code** — monitoring site ID (`station_code`, `ID STN BARU`, `LOCATION`, …)
- **station_name** — human site label (prefer `LOCATION`)
- **river_name** — canonical river (`river_name` column if present; else inferred from `SUNGAI` / code map)
- **DO, BOD, COD, AN, TSS, pH** — parameters (aliases: NH3-N → AN, SS → TSS); optional if **WQI** already in file
- **WQI, river_status** — added or validated in `add_wqi`

Run from project root:
  python -m modules.data_preprocessing.preprocess_dataset
  python -m modules.data_preprocessing.preprocess_dataset --datasets-dir datasets --output-dir datasets/processed
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

# Project root (SmartRiver/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional: use project's WQI calculator and cleaning
try:
    from data_preprocessing.utils.wqi_calculator import (
        normalize_column_names,
        compute_wqi,
        add_wqi_and_status,
    )
    HAS_WQI_CALC = True
except ImportError:
    HAS_WQI_CALC = False

from modules.data_preprocessing.cleaning import (
    remove_duplicates,
    impute_missing,
)

# DOE parameters and column aliases for loading
PARAM_COLS = ["DO", "BOD", "COD", "AN", "TSS", "pH"]
DATE_COL = "date"
STATION_COL = "station_code"

# Date column labels across lab CSVs, DOE exports, and simplified samples
_DATE_SYNONYMS = (
    "date",
    "Date",
    "DATE",
    "reading_date",
    "timestamp",
    "SMP-DAT",
    "SMP_DAT",
    "SMP-DAT ",
    "Tarikh",
    "tarikh",
)

# Prefer true station ID before generic location (avoids duplicate-collapse bugs)
_STATION_SYNONYMS = (
    "station_code",
    "Station Code",
    "station",
    "Station",
    "ID STN BARU",
    "ID STN (2016)",
    "ID STN(2016)",
    " ID STN (2016)",
    "LOCATION",
    "Location",
    "location",
    "SUNGAI",
)


def _strip_column_index(cols: pd.Index) -> pd.Index:
    """Trim BOM/whitespace/newlines from CSV headers (common in DOE exports)."""
    out = []
    for c in cols:
        s = str(c).strip().replace("\ufeff", "").replace("\r", "")
        out.append(s)
    return pd.Index(out)


def _find_first_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    """Resolve first matching column (exact or case-insensitive)."""
    if df is None or df.empty:
        return None
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        lc = cand.strip().lower()
        if lc in lower_map:
            return lower_map[lc]
    return None


def load_dataset(datasets_dir: Path, filename: str | None = None) -> pd.DataFrame:
    """
    Load CSV from datasets folder. If filename is None, use the first CSV found.

    Supports:
    - Simplified monitoring CSV (date, station_code, DO, BOD, …) e.g. sample_water_quality.csv
    - DOE-style exports with SMP-DAT, ID STN BARU, LOCATION, SUNGAI, messy headers (BOD\\nmg/l), etc.
    """
    datasets_dir = Path(datasets_dir)
    if not datasets_dir.is_dir():
        raise FileNotFoundError(f"Datasets directory not found: {datasets_dir}")

    if filename:
        path = datasets_dir / filename
        if not path.suffix.lower() == ".csv":
            path = path.with_suffix(".csv")
    else:
        csvs = list(datasets_dir.glob("*.csv"))
        if not csvs:
            raise FileNotFoundError(f"No CSV files in {datasets_dir}")
        path = csvs[0]

    df = pd.read_csv(path)
    df.columns = _strip_column_index(df.columns)

    # Normalize measurement column names (DO, BOD, …)
    if HAS_WQI_CALC:
        df = normalize_column_names(df)
    else:
        df = _normalize_columns_fallback(df)

    date_src = _find_first_column(df, _DATE_SYNONYMS)
    if date_src:
        # dayfirst=True breaks ISO dates like 2023-01-13 (treated as invalid Y-D-M). Use default parsing.
        df[DATE_COL] = pd.to_datetime(df[date_src], errors="coerce", utc=False)
    else:
        df[DATE_COL] = pd.NaT

    st_src = _find_first_column(df, _STATION_SYNONYMS)
    if st_src:
        df[STATION_COL] = df[st_src].astype(str).str.strip()
    else:
        df[STATION_COL] = "S01"

    # Human-readable site label (prefer LOCATION over junk numeric station_name)
    name_src = _find_first_column(
        df,
        ("LOCATION", "Location", "location", "Station Name", "station_name", "SUNGAI"),
    )
    if name_src:
        df["station_name"] = df[name_src].astype(str).str.strip()
    else:
        df["station_name"] = df[STATION_COL].astype(str)

    # Canonical river_name for dashboard / filters (CSV column or inferred from SUNGAI / station_code)
    river_src = _find_first_column(df, ("river_name", "River Name", "River"))
    if river_src:
        df["river_name"] = df[river_src].astype(str).str.strip()
    else:
        from backend.services.river_mapping import infer_river_name

        sung_col = _find_first_column(df, ("SUNGAI", "Sungai", "sungai"))
        if sung_col:
            df["river_name"] = [
                infer_river_name(sc, sn, sungai=sg)
                for sc, sn, sg in zip(df[STATION_COL], df["station_name"], df[sung_col])
            ]
        else:
            df["river_name"] = [
                infer_river_name(sc, sn)
                for sc, sn in zip(df[STATION_COL], df["station_name"])
            ]

    return df


def _normalize_columns_fallback(df: pd.DataFrame) -> pd.DataFrame:
    """Fallback column renames if wqi_calculator not available."""
    aliases = {
        "do_mg_l": "DO", "bod_mg_l": "BOD", "cod_mg_l": "COD",
        "nh3_n": "AN", "nh3_n_mg_l": "AN", "tss_mg_l": "TSS", "ph": "pH",
    }
    out = df.copy()
    for col in list(out.columns):
        key = str(col).strip().lower().replace(" ", "_")
        if key in aliases:
            out.rename(columns={col: aliases[key]}, inplace=True)
    return out


def data_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """
    Data cleaning: coerce numerics, drop duplicates, drop rows with all params null.
    """
    out = df.copy()
    for c in PARAM_COLS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = remove_duplicates(out, subset=[c for c in [STATION_COL, DATE_COL] if c in out.columns] or None)
    # Drop rows where all DOE params are null
    param_present = [c for c in PARAM_COLS if c in out.columns]
    if param_present:
        out = out.loc[out[param_present].notna().any(axis=1)]
    return out


def missing_value_handling(
    df: pd.DataFrame,
    strategy: str = "median",
) -> pd.DataFrame:
    """
    Handle missing values: 'median', 'mean', or 'drop'.
    """
    cols = [c for c in PARAM_COLS if c in df.columns]
    if not cols:
        return df
    return impute_missing(df, strategy=strategy, columns=cols)


def add_wqi(df: pd.DataFrame) -> pd.DataFrame:
    """Add WQI and river_status columns (DOE Malaysia)."""
    if HAS_WQI_CALC:
        return add_wqi_and_status(df, wqi_column="WQI")
    out = df.copy()
    if "WQI" not in out.columns and all(c in out.columns for c in PARAM_COLS):
        # Minimal WQI: average of normalized 0-100 proxies (simplified)
        wqi = np.zeros(len(out))
        for c in PARAM_COLS:
            x = out[c].fillna(0)
            wqi += np.clip(100 - x * 5, 0, 100)  # crude proxy
        out["WQI"] = wqi / len(PARAM_COLS)
    out["river_status"] = out["WQI"].map(
        lambda x: "clean" if x >= 81 else ("slightly_polluted" if x >= 60 else "polluted")
    )
    return out


def feature_selection(
    df: pd.DataFrame,
    target_col: str = "river_status",
    drop_low_variance: bool = False,
    variance_threshold: float = 1e-5,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Select features for ML: DOE params + WQI (and optional derived).
    Optionally drop near-constant columns.
    Returns (df with selected columns, list of feature names).
    """
    candidate = [c for c in PARAM_COLS + ["WQI"] if c in df.columns]
    if not candidate:
        candidate = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_col]
    out = df.copy()
    if drop_low_variance and candidate:
        from sklearn.feature_selection import VarianceThreshold
        vt = VarianceThreshold(threshold=variance_threshold)
        vt.fit(out[candidate].fillna(0))
        selected = [c for c, m in zip(candidate, vt.get_support()) if m]
    else:
        selected = candidate
    return out, selected


def wqi_normalization(
    df: pd.DataFrame,
    feature_cols: list[str],
    method: str = "minmax",
) -> tuple[pd.DataFrame, object]:
    """
    Normalize WQI and feature columns to [0, 1] (MinMax) or zero-mean unit-var (Standard).
    Returns (df with normalized columns, fitted scaler for later use on test).
    """
    cols = [c for c in feature_cols if c in df.columns]
    if not cols:
        return df, None
    if method == "minmax":
        scaler = MinMaxScaler(feature_range=(0, 1))
    else:
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
    out = df.copy()
    out[cols] = scaler.fit_transform(out[cols].fillna(0))
    return out, scaler


def train_test_split_data(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_col: str = "river_status",
    test_size: float = 0.2,
    random_state: int = 42,
    time_based: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Split into train and test. If time_based and date column exists, split by time;
    otherwise random split.
    Returns (X_train_df, X_test_df, y_train, y_test).
    """
    X = df[feature_cols].fillna(0)
    y = df[target_col] if target_col in df.columns else df["WQI"]

    if time_based and DATE_COL in df.columns:
        df_sorted = df.sort_values(DATE_COL).reset_index(drop=True)
        n = len(df_sorted)
        n_test = max(1, int(n * test_size))
        train_idx = df_sorted.index[:-n_test]
        test_idx = df_sorted.index[-n_test:]
        X_train = X.loc[train_idx]
        X_test = X.loc[test_idx]
        y_train = y.loc[train_idx]
        y_test = y.loc[test_idx]
    else:
        stratify = None
        if target_col in df.columns and df[target_col].dtype.name == "object":
            stratify = y
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=stratify
        )
    return X_train, X_test, y_train, y_test


def run_pipeline(
    datasets_dir: Path = PROJECT_ROOT / "datasets",
    output_dir: Path | None = None,
    filename: str | None = None,
    missing_strategy: str = "median",
    normalize_method: str = "minmax",
    test_size: float = 0.2,
    random_state: int = 42,
    save_outputs: bool = True,
) -> dict:
    """
    Full pipeline: load → clean → missing → WQI → feature selection → normalize → split.
    Optionally saves train/test CSVs and scaler to output_dir.
    """
    datasets_dir = Path(datasets_dir)
    output_dir = Path(output_dir) if output_dir else datasets_dir / "processed"

    # 1. Load
    df = load_dataset(datasets_dir, filename=filename)
    n_raw = len(df)

    # 2. Data cleaning
    df = data_cleaning(df)
    n_after_clean = len(df)

    # 3. Missing value handling
    df = missing_value_handling(df, strategy=missing_strategy)
    n_after_impute = len(df)

    # 4. Add WQI and river_status
    df = add_wqi(df)

    # 5. Feature selection
    df, feature_cols = feature_selection(df, drop_low_variance=False)
    target_col = "river_status" if "river_status" in df.columns else "WQI"

    # 6. WQI normalization (scale features for ML)
    df, scaler = wqi_normalization(df, feature_cols, method=normalize_method)

    # 7. Train-test split
    time_based = DATE_COL in df.columns
    X_train, X_test, y_train, y_test = train_test_split_data(
        df, feature_cols, target_col=target_col, test_size=test_size, random_state=random_state, time_based=time_based
    )

    if save_outputs:
        output_dir.mkdir(parents=True, exist_ok=True)
        train_out = pd.concat([X_train, y_train], axis=1)
        test_out = pd.concat([X_test, y_test], axis=1)
        train_out.to_csv(output_dir / "train.csv", index=False)
        test_out.to_csv(output_dir / "test.csv", index=False)
        if scaler is not None:
            import joblib
            joblib.dump({"scaler": scaler, "feature_columns": feature_cols}, output_dir / "scaler.joblib")
        df.to_csv(output_dir / "preprocessed_full.csv", index=False)

    return {
        "n_raw": n_raw,
        "n_after_clean": n_after_clean,
        "n_after_impute": n_after_impute,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "feature_columns": feature_cols,
        "target_column": target_col,
        "output_dir": str(output_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="Preprocess SmartRiver dataset")
    parser.add_argument("--datasets-dir", type=Path, default=PROJECT_ROOT / "datasets", help="Path to datasets folder")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output for train/test/processed (default: datasets/processed)")
    parser.add_argument("--filename", type=str, default=None, help="CSV filename (default: first CSV in folder)")
    parser.add_argument("--missing", type=str, default="median", choices=["median", "mean", "drop"], help="Missing value strategy")
    parser.add_argument("--normalize", type=str, default="minmax", choices=["minmax", "standard"], help="Normalization method")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test set fraction")
    parser.add_argument("--no-save", action="store_true", help="Do not save train/test CSVs")
    args = parser.parse_args()

    result = run_pipeline(
        datasets_dir=args.datasets_dir,
        output_dir=args.output_dir,
        filename=args.filename,
        missing_strategy=args.missing,
        normalize_method=args.normalize,
        test_size=args.test_size,
        save_outputs=not args.no_save,
    )
    print("Preprocessing done:")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
