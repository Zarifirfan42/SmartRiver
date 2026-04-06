"""
LSTM forecaster for WQI 7–30 days ahead.
Training, evaluation (RMSE, MAE), and prediction.
"""
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

RANDOM_STATE = 42

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


def build_sequences(
    values: np.ndarray,
    seq_len: int,
    horizon: int,
    step: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Build (X, y) for LSTM: X shape (n_samples, seq_len, 1), y shape (n_samples, horizon)."""
    X, y = [], []
    for i in range(0, len(values) - seq_len - horizon + 1, step):
        X.append(values[i : i + seq_len])
        y.append(values[i + seq_len : i + seq_len + horizon])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


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


def _pick_default_station(df: pd.DataFrame) -> Optional[str]:
    """Pick the station with the most rows to avoid mixed-station sequence leakage."""
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
    """
    Naive baseline: predict next steps as the previous timestep (last observed value).
    X_seq shape: (n_samples, seq_len, 1), output shape: (n_samples, horizon)
    """
    if X_seq.ndim == 3:
        last = X_seq[:, -1, 0].reshape(-1, 1)
    elif X_seq.ndim == 2:
        last = X_seq[:, -1].reshape(-1, 1)
    else:
        raise ValueError(f"Expected X_seq with 2 or 3 dims, got shape={X_seq.shape}")
    return np.repeat(last, repeats=horizon, axis=1).astype(np.float32)


def build_model(
    seq_len: int,
    horizon: int,
    lstm_units: tuple = (64, 32),
    dropout: float = 0.2,
) -> Any:
    """Build LSTM model."""
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow is required for LSTM. Install with: pip install tensorflow")

    tf.keras.utils.set_random_seed(RANDOM_STATE)
    model = keras.Sequential([
        layers.Input(shape=(seq_len, 1)),
        layers.LSTM(lstm_units[0], return_sequences=True),
        layers.Dropout(dropout),
        layers.LSTM(lstm_units[1]),
        layers.Dropout(dropout),
        layers.Dense(horizon),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
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
) -> dict[str, Any]:
    """
    Train LSTM on WQI series. Returns model, scaler, metrics (RMSE, MAE), and config.
    """
    if not TF_AVAILABLE:
        return {"error": "TensorFlow not installed", "model": None, "scaler": None, "metrics": {}}

    from sklearn.preprocessing import MinMaxScaler

    selected_station = station_code or _pick_default_station(df)
    series = get_wqi_series(df, station_code=selected_station)
    if len(series) < seq_len + horizon + 10:
        return {"error": "Insufficient data for sequence length and horizon", "model": None, "scaler": None, "metrics": {}}

    scaler = MinMaxScaler(feature_range=(0, 1))
    series_scaled = scaler.fit_transform(series.reshape(-1, 1)).flatten()

    X, y = build_sequences(series_scaled, seq_len, horizon)
    # Keras LSTM expects 3D tensor: (samples, timesteps, features).
    if X.ndim == 2:
        X = X[..., np.newaxis]
    n = len(X)
    n_test = max(1, int(n * test_ratio))
    n_train_val = n - n_test
    if n_train_val < 5:
        return {"error": "Insufficient windows after test split", "model": None, "scaler": None, "metrics": {}}
    n_val = max(1, int(n_train_val * val_ratio))
    n_train = n_train_val - n_val
    if n_train < 3:
        return {"error": "Insufficient windows after validation split", "model": None, "scaler": None, "metrics": {}}

    # Strict chronological split: no shuffle for time series.
    X_train, y_train = X[:n_train], y[:n_train]
    X_val, y_val = X[n_train:n_train + n_val], y[n_train:n_train + n_val]
    X_test, y_test = X[n_train + n_val:], y[n_train + n_val:]

    model = build_model(seq_len, horizon)
    callbacks = []
    if TF_AVAILABLE:
        callbacks.append(
            keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=8, restore_best_weights=True
            )
        )
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        verbose=verbose,
        callbacks=callbacks,
    )

    y_pred_scaled = model.predict(X_test, verbose=0)
    y_pred = scaler.inverse_transform(y_pred_scaled.reshape(-1, horizon)).reshape(y_pred_scaled.shape)
    y_true = scaler.inverse_transform(y_test.reshape(-1, horizon)).reshape(y_test.shape)

    yt = y_true.flatten()
    yp = y_pred.flatten()
    baseline_scaled = _naive_previous_timestep_forecast(X_test, horizon=horizon)
    y_baseline = scaler.inverse_transform(baseline_scaled.reshape(-1, horizon)).reshape(baseline_scaled.shape)
    yb = y_baseline.flatten()

    mse = float(np.mean((yt - yp) ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(yt - yp)))
    r2 = float(r2_score(yt, yp))
    baseline_rmse = float(np.sqrt(np.mean((yt - yb) ** 2)))
    baseline_mae = float(np.mean(np.abs(yt - yb)))
    rmse_improvement_pct = float(((baseline_rmse - rmse) / baseline_rmse) * 100.0) if baseline_rmse > 1e-12 else 0.0
    mae_improvement_pct = float(((baseline_mae - mae) / baseline_mae) * 100.0) if baseline_mae > 1e-12 else 0.0

    metrics = {
        "mse": mse,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "baseline": {
            "strategy": "previous_timestep",
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
            "shuffle": False,
            "station_code_used": selected_station,
        },
    }

    # Keep training loss for transparent model reporting in UI.
    history_dict = history.history if hasattr(history, "history") else {}
    train_loss = list(history_dict.get("loss", []))
    val_loss = list(history_dict.get("val_loss", []))

    return {
        "model": model,
        "scaler": scaler,
        "seq_len": seq_len,
        "horizon": horizon,
        "metrics": metrics,
        "feature_columns": ["WQI"],
        "train_loss": train_loss,
        "val_loss": val_loss,
    }


def predict(
    model: Any,
    scaler: Any,
    last_sequence: np.ndarray,
    horizon: Optional[int] = None,
) -> np.ndarray:
    """Predict next horizon steps. last_sequence shape (seq_len,) or (1, seq_len, 1)."""
    if last_sequence.ndim == 1:
        last_sequence = last_sequence.astype(np.float32).reshape(1, -1, 1)
    pred_scaled = model.predict(last_sequence, verbose=0)
    if horizon is not None:
        pred_scaled = pred_scaled[:, :horizon]
    return scaler.inverse_transform(pred_scaled.reshape(-1, pred_scaled.shape[-1])).flatten()


def save_model(model: Any, scaler: Any, config: dict, path: str | Path) -> None:
    """Save Keras model and scaler."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    model.save(path / "lstm_model.keras")
    joblib.dump({"scaler": scaler, "config": config}, path / "lstm_scaler.joblib")


def load_model(path: str | Path) -> tuple[Any, Any, dict]:
    """Load LSTM model and scaler."""
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow required to load LSTM")
    from tensorflow import keras
    path = Path(path)
    model = keras.models.load_model(path / "lstm_model.keras")
    data = joblib.load(path / "lstm_scaler.joblib")
    return model, data["scaler"], data.get("config", {})
