"""
DOE Malaysia Water Quality Index (WQI) calculation.
Sub-index formulas based on DOE Malaysia standards.
Reference: DOE Malaysia WQI documentation.
"""
import numpy as np
import pandas as pd


# WQI weightings (DOE Malaysia)
WQI_WEIGHTS = {
    "DO": 0.22,   # Dissolved Oxygen
    "BOD": 0.19,  # Biochemical Oxygen Demand
    "COD": 0.16,  # Chemical Oxygen Demand
    "AN": 0.15,   # Ammoniacal Nitrogen (NH3-N)
    "TSS": 0.16,  # Total Suspended Solids
    "pH": 0.12,
}


def sub_index_do(x: float) -> float:
    """Dissolved Oxygen (mg/L). SI=100 when DO>=7.92, 0 when DO<=0."""
    if pd.isna(x) or x < 0:
        return np.nan
    if x >= 7.92:
        return 100.0
    if x <= 0:
        return 0.0
    return -0.395 + 0.030 * (x ** 2) - 0.00020 * (x ** 3)


def sub_index_bod(x: float) -> float:
    """BOD5 (mg/L). Inverse: 100 at 0, 0 at >=20."""
    if pd.isna(x) or x < 0:
        return np.nan
    if x <= 0:
        return 100.0
    if x >= 20:
        return 0.0
    return 100.4 * np.exp(-0.223 * x) - 0.0


def sub_index_cod(x: float) -> float:
    """COD (mg/L). Inverse."""
    if pd.isna(x) or x < 0:
        return np.nan
    if x <= 0:
        return 100.0
    if x >= 200:
        return 0.0
    return -1.33 * x + 133.33 if x <= 100 else -0.5 * x + 50.0


def sub_index_an(x: float) -> float:
    """Ammoniacal Nitrogen NH3-N (mg/L). Inverse."""
    if pd.isna(x) or x < 0:
        return np.nan
    if x <= 0:
        return 100.0
    if x >= 10:
        return 0.0
    return 100.5 * np.exp(-0.393 * x) - 0.0


def sub_index_tss(x: float) -> float:
    """Total Suspended Solids (mg/L). Inverse."""
    if pd.isna(x) or x < 0:
        return np.nan
    if x <= 0:
        return 100.0
    if x >= 500:
        return 0.0
    return 97.0 * np.exp(-0.00676 * x) + 3.0


def sub_index_ph(x: float) -> float:
    """pH. Optimal around 7; decrease towards extremes."""
    if pd.isna(x):
        return np.nan
    if 7.0 <= x <= 8.75:
        return 100.0
    if 5.5 <= x < 7.0:
        return 17.2 * x - 34.4
    if 8.75 < x <= 9.0:
        return 242.0 - 16.2 * x
    return 0.0


SUB_INDEX_FUNCS = {
    "DO": sub_index_do,
    "BOD": sub_index_bod,
    "COD": sub_index_cod,
    "AN": sub_index_an,
    "TSS": sub_index_tss,
    "pH": sub_index_ph,
}

# Common CSV column name variants → standard name
COLUMN_ALIASES = {
    "do": "DO",
    "do_mg_l": "DO",
    "dissolved_oxygen": "DO",
    "bod": "BOD",
    "bod_mg_l": "BOD",
    "bod5": "BOD",
    "cod": "COD",
    "cod_mg_l": "COD",
    "nh3_n": "AN",
    "nh3_n_mg_l": "AN",
    "an": "AN",
    "ammoniacal_nitrogen": "AN",
    "tss": "TSS",
    "tss_mg_l": "TSS",
    "total_suspended_solids": "TSS",
    "ph": "pH",
}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Map common column names to standard DO, BOD, COD, AN, TSS, pH."""
    out = df.copy()
    for col in list(out.columns):
        c = str(col).strip().lower().replace(" ", "_")
        if c in COLUMN_ALIASES:
            out.rename(columns={col: COLUMN_ALIASES[c]}, inplace=True)
    return out


def compute_sub_indices(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all six sub-indices. Expects columns DO, BOD, COD, AN, TSS, pH."""
    out = df.copy()
    for name, func in SUB_INDEX_FUNCS.items():
        if name not in out.columns:
            out[f"SI_{name}"] = np.nan
            continue
        out[f"SI_{name}"] = out[name].astype(float).map(lambda x: func(float(x)) if pd.notna(x) else np.nan)
    return out


def compute_wqi(df: pd.DataFrame) -> pd.Series:
    """
    Compute WQI from sub-indices.
    WQI = sum(weight_i * SI_i) for i in DO, BOD, COD, AN, TSS, pH.
    """
    out = df.copy()
    if "SI_DO" not in out.columns:
        out = compute_sub_indices(out)
    wqi = np.zeros(len(out))
    for name, weight in WQI_WEIGHTS.items():
        si_col = f"SI_{name}"
        if si_col in out.columns:
            wqi += weight * out[si_col].fillna(0).values
    return pd.Series(wqi, index=out.index)


def wqi_to_status(wqi: float) -> str:
    """Map WQI to river status (DOE Malaysia)."""
    if pd.isna(wqi):
        return "unknown"
    w = float(wqi)
    if w >= 81:
        return "clean"
    if w >= 60:
        return "slightly_polluted"
    return "polluted"


def add_wqi_and_status(df: pd.DataFrame, wqi_column: str = "WQI") -> pd.DataFrame:
    """Add WQI and river_status columns. Modifies copy of df."""
    out = df.copy()
    if wqi_column not in out.columns:
        out[wqi_column] = compute_wqi(out)
    out["river_status"] = out[wqi_column].map(wqi_to_status)
    return out
