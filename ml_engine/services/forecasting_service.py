"""
LSTM forecaster for WQI multi-step ahead (Malaysia river data).

- Default (baseline): BiLSTM x2, dropout 0.2, Huber loss, level WQI targets, seq_len=30, chronological split.
- Optional experiments (one at a time recommended): direction_loss_weight > 0 (MSE+direction loss), use_wqi_diff.
- Call set_lstm_random_seeds() or pass seed into train() for reproducible runs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from sklearn.preprocessing import MinMaxScaler

RANDOM_STATE = 42

# Lags used in the LSTM input tensor (days); aligned with sorted daily (or regular) series.
LAG_DAYS: tuple[int, ...] = (1, 7, 30)

# Mutually exclusive monsoon flags (see malaysia_monsoon_features docstring).
MONSOON_FEATURE_COLUMNS: tuple[str, ...] = ("monsoon_ne", "monsoon_sw", "monsoon_other")

# Optional cyclical calendar (adds smooth month signal on top of monsoon binaries).
MONTH_CYCLICAL_COLUMNS: tuple[str, ...] = ("month_sin", "month_cos")

# Raw water-quality columns after pipeline normalize (DOE naming: AN = ammoniacal nitrogen / NH3-N).
LSTM_EXTRA_RAW_PARAMS_DEFAULT: tuple[str, ...] = ("DO", "pH", "AN")


def lstm_feature_column_names(
    include_month_cyclical: bool = False,
    extra_param_columns: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """
    Feature channel order: WQI, lags, monsoon flags, optional month sin/cos, optional raw params.
    Channel 0 stays WQI for naive baseline (last-timestep WQI repeat).
    """
    lag_cols = tuple(f"wqi_lag_{d}" for d in LAG_DAYS)
    base = ("WQI",) + lag_cols + MONSOON_FEATURE_COLUMNS
    if include_month_cyclical:
        base = base + MONTH_CYCLICAL_COLUMNS
    return base + tuple(extra_param_columns)


try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


def set_lstm_random_seeds(seed: int = RANDOM_STATE) -> None:
    """Reproducibility: Python, NumPy, TensorFlow (and Keras) RNGs aligned."""
    import random

    random.seed(seed)
    np.random.seed(seed)
    if TF_AVAILABLE:
        tf.random.set_seed(seed)
        keras.utils.set_random_seed(seed)


def malaysia_monsoon_features(dates: pd.Series) -> pd.DataFrame:
    """
    Binary regime features for Peninsular Malaysia (simplified from MetMalaysia seasons).

    Mutually exclusive columns:
    - monsoon_ne: Northeast monsoon season (roughly Oct–Mar).
    - monsoon_sw: Southwest monsoon (May–Sep).
    - monsoon_other: Remaining months (e.g. April, transitional / weaker monsoon influence).

    Values are float32 in {0.0, 1.0}; exactly one flag is 1 per row.
    """
    dt = pd.to_datetime(dates, errors="coerce")
    month = dt.dt.month
    ne = month.isin([10, 11, 12, 1, 2, 3])
    sw = month.isin([5, 6, 7, 8, 9])
    other = ~(ne | sw)
    return pd.DataFrame(
        {
            "monsoon_ne": ne.astype(np.float32),
            "monsoon_sw": sw.astype(np.float32),
            "monsoon_other": other.astype(np.float32),
        },
        index=dates.index,
    )


def prepare_lstm_frame(
    df: pd.DataFrame,
    station_code: Optional[str] = None,
    date_col: str = "date",
    add_month_cyclical: bool = False,
    extra_param_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    """
    Station-level (or full-frame) table sorted by date with WQI, lag-1/7/30, and monsoon flags.
    Optional ``add_month_cyclical`` appends sin/cos month encoding (seasonality beyond monsoon dummies).
    Optional ``extra_param_columns`` appends normalized raw columns (e.g. DO, pH, AN) when present in ``df``.
    """
    out = df.copy()
    if date_col not in out.columns:
        raise ValueError(f"DataFrame must contain {date_col!r}")
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=[date_col]).sort_values(date_col)
    if station_code is not None and "station_code" in out.columns:
        out = out[out["station_code"].astype(str) == str(station_code)]
    if "WQI" not in out.columns:
        raise ValueError("DataFrame must contain WQI column")
    out = out.reset_index(drop=True)

    group_col = "station_code" if "station_code" in out.columns else None
    for lag in LAG_DAYS:
        col = f"wqi_lag_{lag}"
        if group_col is not None:
            out[col] = out.groupby(group_col, sort=False)["WQI"].shift(lag)
        else:
            out[col] = out["WQI"].shift(lag)
        out[col] = out[col].ffill().bfill()

    mono = malaysia_monsoon_features(out[date_col])
    for c in mono.columns:
        out[c] = mono[c].values

    if add_month_cyclical:
        m = out[date_col].dt.month.fillna(1).astype(np.float64)
        ang = 2.0 * np.pi * (m - 1.0) / 12.0
        out["month_sin"] = np.sin(ang).astype(np.float32)
        out["month_cos"] = np.cos(ang).astype(np.float32)

    for col in extra_param_columns:
        if col not in out.columns:
            out[col] = 0.0
        else:
            out[col] = pd.to_numeric(out[col], errors="coerce")
            if group_col is not None:
                out[col] = out.groupby(group_col, sort=False)[col].ffill().bfill()
            else:
                out[col] = out[col].ffill().bfill()
            out[col] = out[col].fillna(0.0).astype(np.float64)

    return out


def frame_to_arrays(
    prepared: pd.DataFrame,
    feature_columns: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray]:
    """Feature matrix (T, F) and WQI vector (T,) in original units."""
    cols = list(feature_columns)
    missing = [c for c in cols if c not in prepared.columns]
    if missing:
        raise ValueError(f"prepare_lstm_frame missing columns: {missing}")
    feat = prepared[cols].to_numpy(dtype=np.float64)
    wqi = prepared["WQI"].to_numpy(dtype=np.float64)
    feat = np.nan_to_num(feat, nan=0.0, posinf=0.0, neginf=0.0)
    wqi = np.nan_to_num(wqi, nan=0.0, posinf=0.0, neginf=0.0)
    return feat, wqi


def build_sequences(
    values: np.ndarray,
    seq_len: int,
    horizon: int,
    step: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Univariate (legacy): X shape (n_samples, seq_len, 1), y shape (n_samples, horizon)."""
    X, y = [], []
    for i in range(0, len(values) - seq_len - horizon + 1, step):
        X.append(values[i : i + seq_len])
        y.append(values[i + seq_len : i + seq_len + horizon])
    X_arr = np.array(X, dtype=np.float32)
    y_arr = np.array(y, dtype=np.float32)
    if X_arr.ndim == 2:
        X_arr = X_arr[..., np.newaxis]
    return X_arr, y_arr


def build_multivariate_sequences(
    features: np.ndarray,
    wqi: np.ndarray,
    seq_len: int,
    horizon: int,
    step: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """X: (n, seq_len, n_features); y: (n, horizon) future WQI levels."""
    if len(features) != len(wqi):
        raise ValueError("features and wqi must have same length")
    T = len(wqi)
    X, y = [], []
    for i in range(0, T - seq_len - horizon + 1, step):
        X.append(features[i : i + seq_len])
        y.append(wqi[i + seq_len : i + seq_len + horizon])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float64)


def window_anchors_wqi(wqi: np.ndarray, seq_len: int, horizon: int) -> np.ndarray:
    """Anchor WQI (level) at end of each input window: shape (n_windows,)."""
    T = len(wqi)
    return np.array(
        [wqi[i + seq_len - 1] for i in range(0, T - seq_len - horizon + 1)],
        dtype=np.float64,
    )


def targets_level_to_first_diffs(y_level: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    """Per window: diffs of [anchor, y1, ..., yH] -> shape (n, H)."""
    stacked = np.column_stack([anchors, y_level])
    return np.diff(stacked, axis=1).astype(np.float64)


def integrate_diff_to_levels(y_diff: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    """Recover WQI levels from successive first diffs; y_diff and anchors shape (n, H) and (n,)."""
    n, H = y_diff.shape
    out = np.empty((n, H), dtype=np.float64)
    out[:, 0] = anchors + y_diff[:, 0]
    for k in range(1, H):
        out[:, k] = out[:, k - 1] + y_diff[:, k]
    return out


def get_wqi_series(
    df: pd.DataFrame,
    station_code: Optional[str] = None,
    date_col: str = "date",
) -> np.ndarray:
    """Extract WQI time series (sorted by date), optionally for one station."""
    out = df.copy()
    if date_col in out.columns:
        out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
        out = out.dropna(subset=[date_col]).sort_values(date_col)
    if station_code is not None and "station_code" in out.columns:
        out = out[out["station_code"] == station_code]
    if "WQI" not in out.columns:
        raise ValueError("DataFrame must contain WQI column")
    return out["WQI"].values.astype(np.float32)


def build_prediction_window(
    df: pd.DataFrame,
    station_code: Optional[str] = None,
    seq_len: int = 30,
    date_col: str = "date",
    add_month_cyclical: bool = False,
    extra_param_columns: tuple[str, ...] = (),
) -> np.ndarray:
    """
    Last ``seq_len`` rows of LSTM inputs in **original** units, shape (seq_len, n_features).
    Use with ``predict`` after training the multivariate model.
    """
    prepared = prepare_lstm_frame(
        df,
        station_code=station_code,
        date_col=date_col,
        add_month_cyclical=add_month_cyclical,
        extra_param_columns=extra_param_columns,
    )
    cols = list(
        lstm_feature_column_names(
            include_month_cyclical=add_month_cyclical,
            extra_param_columns=extra_param_columns,
        )
    )
    if len(prepared) < seq_len:
        raise ValueError(f"Need at least {seq_len} rows after feature prep; got {len(prepared)}")
    window = prepared[cols].iloc[-seq_len:].to_numpy(dtype=np.float32)
    return np.nan_to_num(window, nan=0.0, posinf=0.0, neginf=0.0)


def _pick_default_station(df: pd.DataFrame) -> Optional[str]:
    if "station_code" not in df.columns:
        return None
    counts = (
        df["station_code"]
        .astype(str)
        .replace("nan", np.nan)
        .dropna()
        .value_counts()
    )
    if counts.empty:
        return None
    return str(counts.index[0])


def _naive_previous_timestep_forecast(X_seq: np.ndarray, horizon: int) -> np.ndarray:
    """Last observed WQI (channel 0) repeated for each horizon step. X_seq (n, seq_len, F)."""
    if X_seq.ndim != 3:
        raise ValueError(f"Expected X_seq (n, seq_len, n_features), got shape={X_seq.shape}")
    last = X_seq[:, -1, 0].reshape(-1, 1)
    return np.repeat(last, repeats=horizon, axis=1).astype(np.float32)


def lstm_regression_extras(y_true_level: np.ndarray, y_pred_level: np.ndarray) -> dict[str, Any]:
    """
    Regression diagnostics on test predictions shaped (n_windows, horizon) or flattened.
    Includes correlation / explained variance; ``direction_step_accuracy`` matches sign of consecutive
    horizon steps (related to the direction loss, not classification accuracy).
    """
    yt = np.asarray(y_true_level, dtype=np.float64)
    yp = np.asarray(y_pred_level, dtype=np.float64)
    if yt.shape != yp.shape:
        raise ValueError("y_true_level and y_pred_level must have the same shape")
    flat_t = yt.ravel()
    flat_p = yp.ravel()
    n = flat_t.size
    mean_true = float(np.mean(flat_t))
    mean_pred = float(np.mean(flat_p))
    var_true = float(np.var(flat_t))
    if n > 1 and np.std(flat_t) > 1e-12 and np.std(flat_p) > 1e-12:
        pearson_r = float(np.corrcoef(flat_t, flat_p)[0, 1])
    else:
        pearson_r = float("nan")
    if var_true > 1e-20:
        explained_var = float(1.0 - np.var(flat_t - flat_p) / var_true)
    else:
        explained_var = float("nan")
    abs_t = np.abs(flat_t)
    mask = abs_t > 1e-3
    mape_pct = (
        float(np.mean(np.abs((flat_t[mask] - flat_p[mask]) / flat_t[mask])) * 100.0) if mask.any() else float("nan")
    )
    median_ae = float(np.median(np.abs(flat_t - flat_p)))
    if yt.ndim == 2 and yt.shape[1] >= 2:
        dt = yt[:, 1:] - yt[:, :-1]
        dp = yp[:, 1:] - yp[:, :-1]
        st = np.sign(dt)
        sp = np.sign(dp)
        mdir = st != 0
        direction_step_accuracy = float(np.mean(st[mdir] == sp[mdir])) if mdir.any() else float("nan")
    else:
        direction_step_accuracy = float("nan")
    within_eps = 5.0
    within_eps_pct = float(np.mean(np.abs(flat_t - flat_p) <= within_eps) * 100.0)
    return {
        "mean_y_true": mean_true,
        "mean_y_pred": mean_pred,
        "mean_bias_pred_minus_true": float(mean_pred - mean_true),
        "pearson_r": pearson_r,
        "explained_variance": explained_var,
        "mape_pct": mape_pct,
        "median_ae": median_ae,
        "direction_step_accuracy": direction_step_accuracy,
        f"within_{int(within_eps)}wqi_points_pct": within_eps_pct,
    }


def wqi_clean_class_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    clean_threshold: float = 81.0,
) -> dict[str, Any]:
    """
    Treat WQI >= ``clean_threshold`` as "clean" (binary). Reports accuracy / precision / recall / F1
    for that positive class so users get familiar classification-style numbers on a regression task.
    """
    yt = (np.asarray(y_true, dtype=np.float64).ravel() >= clean_threshold).astype(np.int32)
    yp = (np.asarray(y_pred, dtype=np.float64).ravel() >= clean_threshold).astype(np.int32)
    tp = int(np.sum((yt == 1) & (yp == 1)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    fn = int(np.sum((yt == 1) & (yp == 0)))
    tn = int(np.sum((yt == 0) & (yp == 0)))
    tot = tp + fp + fn + tn
    accuracy = float((tp + tn) / tot) if tot else 0.0
    precision_clean = float(tp / (tp + fp)) if (tp + fp) else 0.0
    recall_clean = float(tp / (tp + fn)) if (tp + fn) else 0.0
    if precision_clean + recall_clean > 1e-12:
        f1_clean = float(2.0 * precision_clean * recall_clean / (precision_clean + recall_clean))
    else:
        f1_clean = 0.0
    return {
        "clean_threshold_wqi": float(clean_threshold),
        "accuracy": accuracy,
        "precision_clean_class": precision_clean,
        "recall_clean_class": recall_clean,
        "f1_clean_class": f1_clean,
        "confusion_tp_fp_fn_tn": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }


def r2_vs_test_mean(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """
    Coefficient of determination using the **test-set** target mean as baseline:

    R² = 1 - SS_res / SS_tot
    SS_res = sum_i (y_true[i] - y_pred[i])²
    SS_tot = sum_i (y_true[i] - mean(y_true))²   with mean over all test points (flattened).

    This matches sklearn.metrics.r2_score(y_true, y_pred) for 1D inputs.
    """
    yt = np.asarray(y_true, dtype=np.float64).ravel()
    yp = np.asarray(y_pred, dtype=np.float64).ravel()
    n = min(yt.size, yp.size)
    yt = yt[:n]
    yp = yp[:n]
    mu = float(np.mean(yt))
    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - mu) ** 2))
    if ss_tot < 1e-20:
        r2 = float("nan")
    else:
        r2 = float(1.0 - ss_res / ss_tot)
    r2_sk = float(r2_score(yt, yp)) if n > 0 else float("nan")
    return {
        "r2": r2,
        "r2_sklearn": r2_sk,
        "matches_sklearn": bool(np.isfinite(r2) and np.isfinite(r2_sk) and np.isclose(r2, r2_sk, rtol=1e-5)),
        "mean_y_test": mu,
        "ss_res": ss_res,
        "ss_tot": ss_tot,
        "n_points": int(n),
        "formula": "R2 = 1 - sum((y_test - y_pred)^2) / sum((y_test - mean(y_test))^2)",
    }


def save_training_loss_plot(
    train_loss: list[float],
    val_loss: list[float],
    path: str | Path,
    title: str = "LSTM: training vs validation loss",
) -> bool:
    """Save train/val loss curves. Returns False if matplotlib is unavailable or plot fails."""
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    if not train_loss:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    epochs = range(1, len(train_loss) + 1)
    try:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(epochs, train_loss, label="Training loss", color="#2563eb")
        if val_loss and len(val_loss) == len(train_loss):
            ax.plot(epochs, val_loss, label="Validation loss", color="#dc2626")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception:
        return False


def save_test_pred_vs_actual_plot(
    y_actual: np.ndarray,
    y_pred: np.ndarray,
    path: str | Path,
    title: str = "Test set: actual vs predicted WQI (chronological order)",
) -> bool:
    """
    Line plot of flattened test targets in window order (diagnoses flat-lining vs trend following).
    """
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    ya = np.asarray(y_actual, dtype=np.float64).ravel()
    yp = np.asarray(y_pred, dtype=np.float64).ravel()
    n = min(ya.size, yp.size)
    if n < 2:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(np.arange(n), ya[:n], label="Actual WQI", color="#0f172a", lw=1.2, alpha=0.9)
        ax.plot(np.arange(n), yp[:n], label="Predicted WQI", color="#2563eb", lw=1.0, alpha=0.85)
        ax.set_xlabel("Test point index (windows x horizon, time-ordered)")
        ax.set_ylabel("WQI (level space)")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception:
        return False


if TF_AVAILABLE:

    @keras.utils.register_keras_serializable(package="SmartRiver", name="MseDirectionLoss")
    class MseDirectionLoss(keras.losses.Loss):
        """MSE + weighted penalty when consecutive predicted steps move opposite to true step direction (scaled target space)."""

        def __init__(self, horizon: int = 7, direction_weight: float = 0.15, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.horizon = int(horizon)
            self.direction_weight = float(direction_weight)

        def call(self, y_true, y_pred):
            mse = tf.reduce_mean(tf.square(y_true - y_pred))
            if self.horizon <= 1 or self.direction_weight <= 0:
                return mse
            dt = y_true[:, 1:] - y_true[:, :-1]
            dp = y_pred[:, 1:] - y_pred[:, :-1]
            signed = tf.math.sign(dt) * dp
            direction_penalty = tf.reduce_mean(tf.nn.relu(-signed))
            w = tf.cast(self.direction_weight, y_pred.dtype)
            return mse + w * direction_penalty

        def get_config(self) -> dict[str, Any]:
            cfg = super().get_config()
            cfg.update(
                {
                    "horizon": self.horizon,
                    "direction_weight": self.direction_weight,
                }
            )
            return cfg


def build_model(
    seq_len: int,
    horizon: int,
    n_features: int,
    lstm_units: tuple[int, ...] = (64, 32),
    dropout: float = 0.2,
    huber_delta: float = 1.0,
    direction_loss_weight: float = 0.0,
    use_bidirectional: bool = True,
) -> Any:
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow is required for LSTM. Install with: pip install tensorflow")

    units = tuple(int(u) for u in lstm_units)
    if len(units) < 1:
        raise ValueError("lstm_units must contain at least one layer size")

    stack: list[Any] = [layers.Input(shape=(seq_len, n_features))]
    n_layers = len(units)
    for i, u in enumerate(units):
        return_sequences = i < n_layers - 1
        if use_bidirectional:
            stack.append(layers.Bidirectional(layers.LSTM(u, return_sequences=return_sequences)))
        else:
            stack.append(layers.LSTM(u, return_sequences=return_sequences))
        if i < n_layers - 1:
            stack.append(layers.Dropout(dropout))
    stack.append(layers.Dropout(dropout))
    stack.append(layers.Dense(horizon))
    model = keras.Sequential(stack)
    if direction_loss_weight and direction_loss_weight > 0:
        loss: Any = MseDirectionLoss(horizon=horizon, direction_weight=direction_loss_weight)
    else:
        loss = keras.losses.Huber(delta=huber_delta)
    model.compile(optimizer="adam", loss=loss, metrics=["mae"])
    return model


def train(
    df: pd.DataFrame,
    station_code: Optional[str] = None,
    seq_len: int = 30,
    horizon: int = 7,
    test_ratio: float = 0.2,
    val_ratio: float = 0.1,
    epochs: int = 50,
    batch_size: int = 32,
    verbose: int = 0,
    loss_plot_path: Optional[str | Path] = None,
    pred_plot_path: Optional[str | Path] = None,
    early_stopping_patience: int = 10,
    huber_delta: float = 1.0,
    direction_loss_weight: float = 0.0,
    use_wqi_diff: bool = False,
    seed: int = RANDOM_STATE,
    add_month_cyclical: bool = False,
    use_bidirectional: bool = True,
    extra_param_columns: tuple[str, ...] = (),
    lstm_units: tuple[int, ...] = (64, 32),
    dropout: float = 0.2,
) -> dict[str, Any]:
    """
    Train multivariate LSTM (bidirectional by default).

    **Baseline defaults:** Huber loss, WQI level targets, ``seq_len=30``, ``direction_loss_weight=0``,
    ``use_wqi_diff=False``. Set ``direction_loss_weight>0`` for MSE+direction loss, or ``use_wqi_diff=True``
    for first-difference targets (cumsum at inference). ``add_month_cyclical`` adds sin/cos month on top of
    monsoon flags. ``use_bidirectional=False`` uses stacked unidirectional LSTM layers.
    ``extra_param_columns`` appends raw water columns (e.g. ``("DO", "pH", "AN")``) when present in ``df``.
    ``lstm_units`` lists unit sizes per LSTM layer (any length >= 1). ``dropout`` is applied between LSTM layers
    and before the readout Dense layer.
    """
    if not TF_AVAILABLE:
        return {"error": "TensorFlow not installed", "model": None, "scaler": None, "metrics": {}}

    from tensorflow import keras

    set_lstm_random_seeds(seed)

    fc_tuple = lstm_feature_column_names(
        include_month_cyclical=add_month_cyclical,
        extra_param_columns=extra_param_columns,
    )
    feature_columns = list(fc_tuple)
    n_features = len(feature_columns)

    selected_station = station_code or _pick_default_station(df)
    prepared = prepare_lstm_frame(
        df,
        station_code=selected_station,
        add_month_cyclical=add_month_cyclical,
        extra_param_columns=extra_param_columns,
    )
    feat_matrix, wqi_vec = frame_to_arrays(prepared, fc_tuple)
    T = len(wqi_vec)
    if T < seq_len + horizon + 10:
        return {"error": "Insufficient data for sequence length and horizon", "model": None, "scaler": None, "metrics": {}}

    X_win, y_level_win = build_multivariate_sequences(feat_matrix, wqi_vec, seq_len, horizon)
    anchors_win = window_anchors_wqi(wqi_vec, seq_len, horizon)
    y_target_win = (
        targets_level_to_first_diffs(y_level_win, anchors_win) if use_wqi_diff else y_level_win.astype(np.float64)
    )
    n = len(X_win)
    n_test = max(1, int(n * test_ratio))
    n_train_val = n - n_test
    if n_train_val < 5:
        return {"error": "Insufficient windows after test split", "model": None, "scaler": None, "metrics": {}}
    n_val = max(1, int(n_train_val * val_ratio))
    n_train = n_train_val - n_val
    if n_train < 3:
        return {"error": "Insufficient windows after validation split", "model": None, "scaler": None, "metrics": {}}

    train_feat_end = (n_train - 1) + seq_len
    feat_train_rows = feat_matrix[0:train_feat_end]

    scaler_X = MinMaxScaler(feature_range=(0, 1))
    scaler_X.fit(feat_train_rows)
    scaler_y = MinMaxScaler(feature_range=(0, 1))
    if use_wqi_diff:
        scaler_y.fit(y_target_win[:n_train].reshape(-1, 1))
    else:
        wqi_train_slice = wqi_vec[seq_len : n_train + seq_len + horizon - 1]
        scaler_y.fit(wqi_train_slice.reshape(-1, 1))

    feat_all = scaler_X.transform(feat_matrix).astype(np.float32)

    if use_wqi_diff:
        X_full, _ = build_multivariate_sequences(feat_all, wqi_vec, seq_len, horizon)
        y_all_scaled = scaler_y.transform(y_target_win.reshape(-1, 1)).reshape(n, horizon).astype(np.float32)
    else:
        wqi_all = scaler_y.transform(wqi_vec.reshape(-1, 1)).flatten().astype(np.float32)
        X_full, y_all_scaled = build_multivariate_sequences(feat_all, wqi_all, seq_len, horizon)

    X_train = X_full[:n_train]
    y_train = y_all_scaled[:n_train]
    X_val = X_full[n_train : n_train + n_val]
    y_val = y_all_scaled[n_train : n_train + n_val]
    X_test = X_full[n_train + n_val :]
    y_test = y_all_scaled[n_train + n_val :]

    loss_label = "huber" if not (direction_loss_weight and direction_loss_weight > 0) else "mse_plus_direction"
    model = build_model(
        seq_len,
        horizon,
        n_features,
        lstm_units=lstm_units,
        dropout=dropout,
        huber_delta=huber_delta,
        direction_loss_weight=direction_loss_weight,
        use_bidirectional=use_bidirectional,
    )
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=early_stopping_patience,
            restore_best_weights=True,
        )
    ]
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        verbose=verbose,
        callbacks=callbacks,
        shuffle=False,
    )

    y_pred_scaled = model.predict(X_test, verbose=0)
    # scaler_y is univariate (one MinMaxScaler on WQI); flatten horizon dims before inverse_transform.
    y_pred_target = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).reshape(y_pred_scaled.shape)
    anchors_test = anchors_win[n_train + n_val :]
    y_true_level = y_level_win[n_train + n_val :]
    if use_wqi_diff:
        y_pred = integrate_diff_to_levels(y_pred_target, anchors_test)
    else:
        y_pred = y_pred_target

    yt = y_true_level.flatten()
    yp = y_pred.flatten()
    if use_wqi_diff:
        y_baseline = np.repeat(anchors_test[:, np.newaxis], horizon, axis=1)
    else:
        baseline_scaled = _naive_previous_timestep_forecast(X_test, horizon=horizon)
        y_baseline = scaler_y.inverse_transform(baseline_scaled.reshape(-1, 1)).reshape(baseline_scaled.shape)
    yb = y_baseline.flatten()

    mse = float(np.mean((yt - yp) ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(yt - yp)))
    r2_detail = r2_vs_test_mean(yt, yp)
    reg_extra = lstm_regression_extras(y_true_level, y_pred)
    clean_cls = wqi_clean_class_metrics(y_true_level, y_pred)
    baseline_rmse = float(np.sqrt(np.mean((yt - yb) ** 2)))
    baseline_mae = float(np.mean(np.abs(yt - yb)))
    rmse_improvement_pct = float(((baseline_rmse - rmse) / baseline_rmse) * 100.0) if baseline_rmse > 1e-12 else 0.0
    mae_improvement_pct = float(((baseline_mae - mae) / baseline_mae) * 100.0) if baseline_mae > 1e-12 else 0.0

    scaler_bundle: dict[str, Any] = {"scaler_X": scaler_X, "scaler_y": scaler_y}
    if use_wqi_diff:
        scaler_bundle["target_wqi_diff"] = True

    metrics = {
        "mse": mse,
        "rmse": rmse,
        "mae": mae,
        "r2": r2_detail["r2"],
        "r2_vs_test_mean": r2_detail,
        "regression_extras": reg_extra,
        "wqi_clean_binary_at_81": clean_cls,
        "baseline": {
            "strategy": "repeat_anchor_wqi" if use_wqi_diff else "previous_timestep_wqi",
            "rmse": baseline_rmse,
            "mae": baseline_mae,
        },
        "improvement_vs_baseline_pct": {
            "rmse": rmse_improvement_pct,
            "mae": mae_improvement_pct,
        },
        "split_info": {
            "n_sequences_total": int(n),
            "n_train": int(len(X_train)),
            "n_val": int(len(X_val)),
            "n_test": int(len(X_test)),
            "test_ratio": float(test_ratio),
            "val_ratio_of_train_val": float(val_ratio),
            "shuffle_windows": False,
            "keras_fit_shuffle": False,
            "station_code_used": selected_station,
            "lag_days": list(LAG_DAYS),
            "monsoon_features": list(MONSOON_FEATURE_COLUMNS),
            "loss": loss_label,
            "huber_delta": float(huber_delta),
            "direction_loss_weight": float(direction_loss_weight),
            "target_wqi_diff": bool(use_wqi_diff),
            "random_seed": int(seed),
            "add_month_cyclical": bool(add_month_cyclical),
            "use_bidirectional": bool(use_bidirectional),
            "extra_param_columns": list(extra_param_columns),
            "lstm_units": list(lstm_units),
            "dropout": float(dropout),
            "architecture": (
                f"{len(lstm_units)}x_bidirectional_lstm"
                if use_bidirectional
                else f"{len(lstm_units)}x_lstm_unidirectional"
            ),
            "early_stopping_patience": early_stopping_patience,
            "seq_len": int(seq_len),
        },
    }

    history_dict = history.history if hasattr(history, "history") else {}
    train_loss = [float(x) for x in history_dict.get("loss", [])]
    val_loss = [float(x) for x in history_dict.get("val_loss", [])]

    loss_title = (
        "LSTM: training vs validation loss (Huber)"
        if loss_label == "huber"
        else "LSTM: training vs validation loss (MSE + direction)"
    )
    loss_plot_saved: Optional[str] = None
    if loss_plot_path is not None:
        if save_training_loss_plot(train_loss, val_loss, loss_plot_path, title=loss_title):
            loss_plot_saved = str(Path(loss_plot_path).resolve())
            if verbose:
                print(f"[LSTM] Saved loss plot: {loss_plot_saved}")

    pred_plot_saved: Optional[str] = None
    if pred_plot_path is not None:
        if save_test_pred_vs_actual_plot(yt, yp, pred_plot_path):
            pred_plot_saved = str(Path(pred_plot_path).resolve())
            if verbose:
                print(f"[LSTM] Saved pred vs actual plot: {pred_plot_saved}")

    config = {
        "seq_len": seq_len,
        "horizon": horizon,
        "n_features": n_features,
        "feature_columns": feature_columns,
        "multivariate": True,
        "lag_days": list(LAG_DAYS),
        "loss": loss_label,
        "huber_delta": float(huber_delta),
        "direction_loss_weight": float(direction_loss_weight),
        "target_wqi_diff": bool(use_wqi_diff),
        "random_seed": int(seed),
        "add_month_cyclical": bool(add_month_cyclical),
        "use_bidirectional": bool(use_bidirectional),
        "extra_param_columns": list(extra_param_columns),
        "lstm_units": list(lstm_units),
        "dropout": float(dropout),
        "architecture": (
            f"{len(lstm_units)}x_bidirectional_lstm"
            if use_bidirectional
            else f"{len(lstm_units)}x_lstm_unidirectional"
        ),
        "early_stopping_patience": int(early_stopping_patience),
    }

    return {
        "model": model,
        "scaler": scaler_bundle,
        "seq_len": seq_len,
        "horizon": horizon,
        "metrics": metrics,
        "feature_columns": feature_columns,
        "train_loss": train_loss,
        "val_loss": val_loss,
        "config": config,
        "loss_plot_path": loss_plot_saved,
        "pred_vs_actual_plot_path": pred_plot_saved,
    }


def _outputs_are_fraction_wqi(scaler_y: Any) -> bool:
    """True when targets were fit in ~0–1 (fraction) rather than DOE 0–100 scale."""
    try:
        dmax = float(np.max(scaler_y.data_max_))
        dmin = float(np.min(scaler_y.data_min_))
    except Exception:
        return False
    return dmax <= 1.5 and dmin >= -0.5


def _to_display_wqi(arr: np.ndarray, scaler_y: Any) -> np.ndarray:
    """Map inverse-transformed targets to 0–100 WQI for dashboard when training used 0–1 targets."""
    out = np.asarray(arr, dtype=np.float64)
    if _outputs_are_fraction_wqi(scaler_y):
        out = out * 100.0
    return np.clip(out, 0.0, 100.0).astype(np.float32)


def predict(
    model: Any,
    scaler_bundle: Any,
    window: np.ndarray,
    horizon: Optional[int] = None,
) -> np.ndarray:
    """
    Forecast next ``horizon`` WQI steps.

    ``window`` must be either:
    - (seq_len, n_features) raw features in the same column order as ``lstm_feature_column_names()``, or
    - (seq_len,) legacy univariate scaled WQI (older models with single MinMaxScaler on WQI only).
    """
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow required for LSTM prediction")

    window = np.asarray(window, dtype=np.float32)

    if isinstance(scaler_bundle, dict) and "scaler_X" in scaler_bundle and "scaler_y" in scaler_bundle:
        if window.ndim != 2:
            raise ValueError(f"Multivariate model expects window shape (seq_len, n_features), got {window.shape}")
        scaler_X = scaler_bundle["scaler_X"]
        scaler_y = scaler_bundle["scaler_y"]
        use_diff = bool(scaler_bundle.get("target_wqi_diff", False))
        x_flat = scaler_X.transform(window.reshape(-1, window.shape[-1]))
        seq_len, n_feat = window.shape
        x_scaled = x_flat.astype(np.float32).reshape(1, seq_len, n_feat)
        pred_scaled = model.predict(x_scaled, verbose=0)
        if horizon is not None:
            pred_scaled = pred_scaled[:, :horizon]
        h = pred_scaled.shape[1]
        pred_target = scaler_y.inverse_transform(pred_scaled.reshape(-1, 1)).reshape(pred_scaled.shape[0], h)
        if use_diff:
            anchor = float(window[-1, 0])
            row = pred_target[0].astype(np.float64)
            levels = np.empty(h, dtype=np.float64)
            levels[0] = anchor + row[0]
            for k in range(1, h):
                levels[k] = levels[k - 1] + row[k]
            return _to_display_wqi(levels, scaler_y)
        return _to_display_wqi(pred_target.flatten(), scaler_y)

    # Legacy: single scaler on WQI, window 1D length seq_len (scaled values).
    scaler = scaler_bundle
    if window.ndim == 1:
        w = window.reshape(1, -1, 1)
    elif window.ndim == 2 and window.shape[1] == 1:
        w = window.reshape(1, window.shape[0], 1)
    else:
        raise ValueError(f"Legacy predict expects 1D scaled WQI window; got shape {window.shape}")
    pred_scaled = model.predict(w, verbose=0)
    if horizon is not None:
        pred_scaled = pred_scaled[:, :horizon]
    inv = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
    return _to_display_wqi(inv, scaler)


def save_model(model: Any, scaler_bundle: Any, config: dict, path: str | Path) -> None:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    model.save(path / "lstm_model.keras")
    joblib.dump({"scaler": scaler_bundle, "config": config}, path / "lstm_scaler.joblib")


def load_model(path: str | Path) -> tuple[Any, Any, dict]:
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow required to load LSTM")
    from tensorflow import keras

    path = Path(path)
    meta_path = path / "lstm_scaler.joblib"
    if not meta_path.is_file():
        meta_path = path / "scaler.joblib"
    data = joblib.load(meta_path)
    cfg = data.get("config", {}) or {}
    h = int(cfg.get("horizon", 7))
    dw = float(cfg.get("direction_loss_weight", 0.0))
    huber_d = float(cfg.get("huber_delta", 1.0))
    custom_objects = {"MseDirectionLoss": MseDirectionLoss}
    model_path = path / "lstm_model.keras"
    if not model_path.is_file():
        model_path = path / "model.keras"

    try:
        model = keras.models.load_model(model_path, compile=True)
    except Exception:
        try:
            model = keras.models.load_model(model_path, custom_objects=custom_objects, compile=True)
        except Exception:
            try:
                model = keras.models.load_model(model_path, compile=False)
            except Exception:
                model = keras.models.load_model(model_path, custom_objects=custom_objects, compile=False)
            if dw > 0:
                model.compile(
                    optimizer="adam",
                    loss=MseDirectionLoss(horizon=h, direction_weight=dw),
                    metrics=["mae"],
                )
            else:
                model.compile(
                    optimizer="adam",
                    loss=keras.losses.Huber(delta=huber_d),
                    metrics=["mae"],
                )
    return model, data["scaler"], cfg
