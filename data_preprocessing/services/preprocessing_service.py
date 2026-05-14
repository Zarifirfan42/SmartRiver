"""
Orchestrate load → clean → impute → WQI → feature engineering.
Delegates to pipeline.run_pipeline.
"""
from pathlib import Path
from typing import Optional, Literal

import pandas as pd

from data_preprocessing.services.pipeline import run_pipeline


def run_preprocessing(
    input_path: str | Path,
    output_path: Optional[str | Path] = None,
    missing_strategy: Literal["mean", "median", "drop"] = "median",
    remove_duplicates: bool = True,
    rolling_window: int = 7,
    lag_days: tuple = (1, 7, 14),
    normalize: bool = True,
) -> pd.DataFrame:
    """
    Run full preprocessing pipeline and optionally save result.
    Returns DataFrame with WQI, river_status, and engineered features.
    """
    return run_pipeline(
        input_path,
        output_path=output_path,
        missing_strategy=missing_strategy,
        remove_duplicates=remove_duplicates,
        rolling_window=rolling_window,
        lag_days=lag_days,
        normalize=normalize,
    )
