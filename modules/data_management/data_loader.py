"""
Data loader — Load and validate CSV datasets (DOE Malaysia format).
Used by data_preprocessing pipeline and dataset upload flow.
"""
from pathlib import Path
from typing import Optional, List
import pandas as pd


# Expected columns for DOE water quality CSV (after normalization)
EXPECTED_COLUMNS = ["date", "station_code", "DO", "BOD", "COD", "AN", "TSS", "pH"]


def load_csv(path: str | Path) -> pd.DataFrame:
    """
    Load CSV from path. Normalize column names to standard DOE format.
    """
    path = Path(path)
    if not path.suffix.lower() == ".csv":
        raise ValueError("File must be a CSV")
    df = pd.read_csv(path)
    return normalize_columns(df)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map common column names to DO, BOD, COD, AN (NH3-N), TSS, pH."""
    aliases = {
        "do_mg_l": "DO", "dissolved_oxygen": "DO",
        "bod_mg_l": "BOD", "bod5": "BOD",
        "cod_mg_l": "COD",
        "nh3_n": "AN", "nh3_n_mg_l": "AN", "ammoniacal_nitrogen": "AN",
        "tss_mg_l": "TSS", "total_suspended_solids": "TSS",
    }
    out = df.copy()
    for col in list(out.columns):
        key = str(col).strip().lower().replace(" ", "_")
        if key in aliases:
            out.rename(columns={col: aliases[key]}, inplace=True)
    return out


def validate_columns(df: pd.DataFrame) -> List[str]:
    """Return list of missing required columns. Empty if valid."""
    missing = []
    for c in ["DO", "BOD", "COD", "AN", "TSS", "pH"]:
        if c not in df.columns:
            missing.append(c)
    return missing
