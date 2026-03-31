"""
River entity mapping for SmartRiver (FYP / examiner-friendly).

Purpose:
- Link technical station codes (S01, S02, …) to real-world river names users recognise.
- Keep one configurable dictionary so behaviour is explicit and easy to extend.

Design (Option A):
- Primary key remains station_code in data and ML pipeline (unchanged).
- river_name is a display + filter dimension derived from station_code (and optional CSV station name).

Add or edit RIVER_NAME_BY_STATION_CODE for your deployment. Unknown codes resolve to UNKNOWN_RIVER_LABEL.
"""
from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Configurable map: station_code → canonical river name (Malaysia examples)
# Extend with new codes (e.g. S06) without changing ML feature columns.
# ---------------------------------------------------------------------------
RIVER_NAME_BY_STATION_CODE: dict[str, str] = {
    "S01": "Sungai Klang",
    "S02": "Sungai Gombak",
    # Sample CSV uses S03 here; swap to "Sungai Muda" if your deployment maps S03 to Muda.
    "S03": "Sungai Pinang",
    "S04": "Sungai Kulim",
    "S05": "Sungai Perak",
    "S06": "Sungai Muda",
}

UNKNOWN_RIVER_LABEL = "Unknown River"

# DOE basin / short labels (e.g. SUNGAI column) → display name used in dashboard filters
SUNGAI_BASIN_TO_RIVER: dict[str, str] = {
    "KULIM": "Sungai Kulim",
    "KLANG": "Sungai Klang",
    "PINANG": "Sungai Pinang",
    "PENANG": "Sungai Pinang",
    "PERAK": "Sungai Perak",
    "GOMBAK": "Sungai Gombak",
    "MUDA": "Sungai Muda",
}


def river_name_from_sungai(sungai: Optional[str]) -> Optional[str]:
    """Map DOE 'SUNGAI' / basin token to canonical river name, or None if unknown."""
    if sungai is None:
        return None
    try:
        if isinstance(sungai, float) and sungai != sungai:  # NaN
            return None
    except (TypeError, ValueError):
        pass
    s = str(sungai).strip()
    if not s:
        return None
    u = s.upper()
    if u in SUNGAI_BASIN_TO_RIVER:
        return SUNGAI_BASIN_TO_RIVER[u]
    if u.startswith("SUNGAI "):
        return s.strip().title()
    return f"Sungai {s.title()}"


def infer_river_name(
    station_code: Optional[str],
    station_name: Optional[str] = None,
    sungai: Optional[str] = None,
    explicit_river: Optional[str] = None,
) -> str:
    """
    Single entry point after load: explicit CSV river_name > SUNGAI mapping > S01-style map > labels.
    """
    if explicit_river and str(explicit_river).strip():
        return str(explicit_river).strip()
    rs = river_name_from_sungai(sungai)
    if rs:
        return rs
    return river_name_for_station(station_code, station_name)


def normalize_station_code(code: Optional[str]) -> str:
    """Uppercase strip for lookup consistency."""
    if code is None:
        return ""
    return str(code).strip().upper()


def river_name_for_station(
    station_code: Optional[str],
    station_name: Optional[str] = None,
) -> str:
    """
    Resolve canonical river_name for a row.

    1) Prefer explicit mapping from station_code.
    2) If station_name already looks like 'Sungai …', use it when code unknown.
    3) Otherwise unknown code → UNKNOWN_RIVER_LABEL.
    """
    code = normalize_station_code(station_code)
    if code and code in RIVER_NAME_BY_STATION_CODE:
        return RIVER_NAME_BY_STATION_CODE[code]
    name = (station_name or "").strip()
    if name.startswith("Sungai "):
        return name
    if name and code:
        return f"{name} ({code})" if name not in RIVER_NAME_BY_STATION_CODE.values() else name
    return UNKNOWN_RIVER_LABEL if name == "" else name


def river_names_from_upload_station_codes(codes: list[str]) -> tuple[list[str], list[str]]:
    """
    For admin upload validation: return (resolved_river_names, unknown_codes).

    unknown_codes lists codes not present in RIVER_NAME_BY_STATION_CODE (still allowed;
    they map to UNKNOWN_RIVER_LABEL unless you enable strict mode in upload handler).
    """
    seen: list[str] = []
    unknown: list[str] = []
    for c in codes:
        code = normalize_station_code(c)
        if not code:
            continue
        if code not in RIVER_NAME_BY_STATION_CODE:
            unknown.append(code)
        rn = river_name_for_station(code, None)
        if rn not in seen:
            seen.append(rn)
    return seen, unknown


def reading_matches_river(rec: dict, river_name: Optional[str]) -> bool:
    """True if reading should be included when filtering by river_name."""
    if not river_name or not str(river_name).strip():
        return True
    target = str(river_name).strip()
    rn = (rec.get("river_name") or "").strip()
    if rn and rn == target:
        return True
    code = normalize_station_code(rec.get("station_code"))
    name = (rec.get("station_name") or "").strip()
    return river_name_for_station(code, name) == target or name == target or code == target


def forecast_point_matches_river(point: dict, river_name: Optional[str]) -> bool:
    """Filter forecast JSON points by river_name."""
    if not river_name or not str(river_name).strip():
        return True
    target = str(river_name).strip()
    code = normalize_station_code(point.get("station_code"))
    name = (point.get("station_name") or "").strip()
    return river_name_for_station(code, name) == target or name == target or code == target


def station_codes_from_csv_bytes(content: bytes, max_rows: int = 12000) -> tuple[list[str], Optional[str]]:
    """
    Peek at an uploaded CSV and return distinct station_code values (uppercased trimmed).

    Returns (codes, error). error is set if the file cannot be parsed or no station column exists.
    Used by admin upload to derive river_name and validate against RIVER_NAME_BY_STATION_CODE.
    """
    import io

    try:
        import pandas as pd
    except ImportError:
        return [], "pandas not available"

    try:
        df = pd.read_csv(io.BytesIO(content), nrows=max_rows)
    except Exception as e:
        return [], str(e)

    if df is None or df.empty:
        return [], "empty csv"

    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]
    lower_map = {str(c).strip().lower(): c for c in df.columns}

    for col in (
        "station_code",
        "Station Code",
        "station code",
        "STATION_CODE",
        "ID STN (2016)",
        "ID STN BARU",
        "ID_STN",
    ):
        key = col.strip().lower()
        real = col if col in df.columns else lower_map.get(key)
        if real is None:
            continue
        raw = df[real].dropna().astype(str).str.strip()
        codes = sorted({normalize_station_code(x) for x in raw.tolist() if normalize_station_code(x)})
        if codes:
            return codes, None

    return [], "no station_code column found (add Station Code / station_code column)"


def dataset_upload_metadata_from_csv(content: bytes) -> dict:
    """
    Derive river_name and validation warnings from raw CSV bytes (admin upload).

    - If no station_code column: returns parse_error (caller may still save file without river metadata).
    - Unknown codes: warning + rows resolve to Unknown River via river_name_for_station (unless strict env).
    """
    import os

    codes, err = station_codes_from_csv_bytes(content)
    out: dict = {
        "station_codes_seen": codes,
        "river_name": None,
        "unknown_station_codes": [],
        "warnings": [],
        "parse_error": err,
    }
    if err:
        out["warnings"].append(err)
        return out

    unknown = [c for c in codes if c not in RIVER_NAME_BY_STATION_CODE]
    out["unknown_station_codes"] = list(unknown)
    for u in unknown:
        out["warnings"].append(
            f"Station code {u} is not in RIVER_NAME_BY_STATION_CODE; readings will use '{UNKNOWN_RIVER_LABEL}'."
        )

    strict = (os.environ.get("SMARTRIVER_STRICT_STATION_CODES") or "").strip().lower() in ("1", "true", "yes")
    if strict and unknown:
        out["reject"] = True
        out["reject_detail"] = f"Unknown station codes: {unknown}. Add them to RIVER_NAME_BY_STATION_CODE or disable SMARTRIVER_STRICT_STATION_CODES."
        return out

    labels = sorted({river_name_for_station(c, None) for c in codes})
    out["river_name"] = labels[0] if len(labels) == 1 else "Multiple rivers"
    return out
