"""
Lightweight data augmentation helpers for time-series WQI.

This module never overwrites the original dataset. It only creates
an augmented copy in memory to help LSTM training when data is small.
"""
from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd


def augment_wqi_series(
    df: pd.DataFrame,
    min_rows: int = 120,
    noise_std: float = 1.2,
    random_state: int = 42,
    date_col: str = "date",
    wqi_col: str = "WQI",
) -> pd.DataFrame:
    """
    Return an augmented DataFrame when row count is small.

    Strategy (simple for FYP presentation):
    - If data already has enough rows, return original copy.
    - Otherwise, duplicate rows with small Gaussian noise on WQI.
    - Clamp WQI into realistic [0, 100].
    """
    out = df.copy()
    if wqi_col not in out.columns:
        return out

    if len(out) >= min_rows:
        return out

    rng = np.random.default_rng(random_state)
    needed = max(0, min_rows - len(out))
    if needed == 0 or len(out) == 0:
        return out

    sampled = out.sample(n=needed, replace=True, random_state=random_state).copy()
    noise = rng.normal(0.0, noise_std, size=len(sampled))
    sampled[wqi_col] = np.clip(sampled[wqi_col].astype(float).values + noise, 0.0, 100.0)

    # Keep chronology stable if date column exists.
    if date_col in sampled.columns:
        sampled[date_col] = pd.to_datetime(sampled[date_col], errors="coerce")
        sampled = sampled.sort_values(date_col)

    augmented = pd.concat([out, sampled], ignore_index=True)
    if date_col in augmented.columns:
        augmented[date_col] = pd.to_datetime(augmented[date_col], errors="coerce")
        augmented = augmented.sort_values(date_col).reset_index(drop=True)
    return augmented

