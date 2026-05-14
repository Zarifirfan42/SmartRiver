"""
Diagnose negative R² for SmartRiver LSTM WQI forecaster (ml_engine.services.forecasting_service).

Run from project root:
  python -m ml_engine.diagnose_lstm_r2
  python -m ml_engine.diagnose_lstm_r2 --csv datasets/sample_water_quality.csv --no-by-river

With TensorFlow + matplotlib: also trains a short LSTM, verifies R² numerically, saves a scatter plot.
Without TensorFlow: still prints split type, WQI distributions, and R² formula.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _r2_manual(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Same as sklearn.metrics.r2_score for 1D arrays (unweighted OLS definition)."""
    y_true = np.asarray(y_true, dtype=np.float64).ravel()
    y_pred = np.asarray(y_pred, dtype=np.float64).ravel()
    ss_res = np.sum((y_true - y_pred) ** 2)
    y_mean = np.mean(y_true)
    ss_tot = np.sum((y_true - y_mean) ** 2)
    if ss_tot < 1e-20:
        return float("nan")
    return float(1.0 - ss_res / ss_tot)


def _print_causes() -> None:
    print("\n" + "=" * 72)
    print("LIKELY CAUSES OF NEGATIVE R^2 (biggest impact first)")
    print("=" * 72)
    print("  a) Metric on flattened multi-step targets: one R^2 mixes h+1..h+7 errors; hard steps drag it down.")
    print("  b) Non-stationary WQI on the test tail: model fits earlier regime; tail mean/variance differ.")
    print("  c) Weak signal / overfitting: LSTM may not beat mean(y_test) on that segment.")
    print("  d) MinMaxScaler fit on full series before split leaks scale stats (usually hurts less than a,b).")
    print("\nSuggested fixes (highest impact typical):")
    print("  - Report per-horizon RMSE/R^2 or only step-1 R^2 for interpretability.")
    print("  - Fit scaler only on training portion of the raw series, then transform all (no leakage).")
    print("  - Add seasonality features or detrend; try longer seq_len if data supports it.")
    print("  - More data per station; avoid mixing stations in one series unless model is multi-station aware.")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description="LSTM R² diagnostics for SmartRiver")
    parser.add_argument("--csv", type=str, default=None, help="CSV path or filename under datasets/")
    parser.add_argument("--datasets-dir", type=Path, default=PROJECT_ROOT / "datasets")
    parser.add_argument("--no-by-river", action="store_true")
    parser.add_argument("--year-from", type=int, default=None)
    parser.add_argument("--year-to", type=int, default=None)
    parser.add_argument("--plot", type=Path, default=PROJECT_ROOT / "ml_engine" / "lstm_actual_vs_predicted_test.png")
    args = parser.parse_args()

    from sklearn.metrics import r2_score
    from sklearn.preprocessing import MinMaxScaler

    from data_preprocessing.services.pipeline import ingest_csv, ingest_many_csv, clean_data, impute_missing, add_wqi, feature_engineering
    from ml_engine.train import _collect_training_csv_paths, _filter_by_calendar_years
    from ml_engine.services.forecasting_service import (
        TF_AVAILABLE,
        build_model,
        build_sequences,
        get_wqi_series,
        _pick_default_station,
        RANDOM_STATE,
    )

    paths = _collect_training_csv_paths(
        Path(args.datasets_dir),
        args.csv,
        use_by_river=not args.no_by_river,
    )
    if len(paths) == 1:
        df_raw = ingest_csv(paths[0])
    else:
        df_raw = ingest_many_csv(paths)
    df_raw = _filter_by_calendar_years(df_raw, args.year_from, args.year_to)
    df_base = clean_data(df_raw, remove_duplicates=True)
    df_base = impute_missing(df_base, strategy="median")
    df_base = add_wqi(df_base)
    df, _ = feature_engineering(df_base, rolling_window=7, lag_days=[1, 7, 14], normalize=True)

    seq_len, horizon = 30, 7
    test_ratio, val_ratio = 0.2, 0.1
    station_code = _pick_default_station(df)

    series = get_wqi_series(df, station_code=station_code)
    print("=" * 72)
    print("1) SPLIT TYPE")
    print("=" * 72)
    print("forecasting_service.train() uses CHRONOLOGICAL splits on sequence windows (not random):")
    print("  X_train, y_train = X[:n_train], y[:n_train]")
    print("  X_val,   y_val   = X[n_train:n_train+n_val], ...")
    print("  X_test,  y_test  = X[n_train+n_val:], ...")
    print("  shuffle = False (no train_test_split on windows).")
    print(f"  Station used: {station_code!r}, series length: {len(series)}")

    scaler = MinMaxScaler(feature_range=(0, 1))
    series_scaled = scaler.fit_transform(series.reshape(-1, 1)).flatten()
    X, y = build_sequences(series_scaled, seq_len, horizon)
    if X.ndim == 2:
        X = X[..., np.newaxis]
    n = len(X)
    n_test = max(1, int(n * test_ratio))
    n_train_val = n - n_test
    n_val = max(1, int(n_train_val * val_ratio))
    n_train = n_train_val - n_val

    X_train, y_train = X[:n_train], y[:n_train]
    X_val, y_val = X[n_train : n_train + n_val], y[n_train : n_train + n_val]
    X_test, y_test = X[n_train + n_val :], y[n_train + n_val :]

    # WQI targets in original units (all horizon steps per window)
    wqi_train = scaler.inverse_transform(y_train.reshape(-1, horizon)).reshape(y_train.shape)
    wqi_val = scaler.inverse_transform(y_val.reshape(-1, horizon)).reshape(y_val.shape)
    wqi_test = scaler.inverse_transform(y_test.reshape(-1, horizon)).reshape(y_test.shape)

    def stats(name: str, arr: np.ndarray) -> None:
        a = arr.astype(np.float64).ravel()
        print(f"\n{name} (all target WQI values in split, flattened over windows x horizon={horizon})")
        print(f"  n points: {a.size}")
        print(f"  mean: {np.mean(a):.4f}  std: {np.std(a):.4f}  min: {np.min(a):.4f}  max: {np.max(a):.4f}")

    print("\n" + "=" * 72)
    print("2) TRAIN vs VAL vs TEST - WQI distribution (targets y, original scale)")
    print("=" * 72)
    stats("TRAIN targets", wqi_train)
    stats("VAL targets", wqi_val)
    stats("TEST targets", wqi_test)
    d_mean = float(np.mean(wqi_test) - np.mean(wqi_train))
    d_std = float(np.std(wqi_test) - np.std(wqi_train))
    print(f"\n  Shift test vs train: d_mean={d_mean:+.4f}  d_std={d_std:+.4f}")
    if abs(d_mean) > 3 or abs(d_std) > 5:
        print("  >>> Large distribution shift on the held-out tail can hurt R^2 even with chronological split.")

    print("\n" + "=" * 72)
    print("3) R^2 DEFINITION (sklearn.metrics.r2_score, default multioutput=uniform_average)")
    print("=" * 72)
    print("For flattened y_true, y_pred (1D):")
    print("  R^2 = 1 - SS_res / SS_tot")
    print("  SS_res = sum_i (y_true[i] - y_pred[i])^2")
    print("  SS_tot = sum_i (y_true[i] - mean(y_true))^2   (mean is over TEST points only)")
    print("If SS_res > SS_tot  =>  R^2 < 0  (model worse than predicting constant mean(y_test)).")

    if not TF_AVAILABLE:
        print("\n" + "=" * 72)
        print("4) LSTM / R^2 numeric check / plot - skipped (TensorFlow not installed)")
        print("=" * 72)
        print("  pip install tensorflow matplotlib  then re-run for sklearn vs manual R^2 and scatter plot.")
        _print_causes()
        return 0

    from tensorflow import keras

    keras.utils.set_random_seed(RANDOM_STATE)
    n_feat = X_train.shape[-1] if X_train.ndim == 3 else 1
    model = build_model(seq_len, horizon, n_features=n_feat)
    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)
    ]
    model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=32,
        verbose=0,
        callbacks=callbacks,
        shuffle=False,
    )
    y_pred_scaled = model.predict(X_test, verbose=0)
    y_pred = scaler.inverse_transform(y_pred_scaled.reshape(-1, horizon)).reshape(y_pred_scaled.shape)

    yt = wqi_test.reshape(-1)
    yp = y_pred.reshape(-1)

    r2_sk = float(r2_score(yt, yp))
    r2_man = _r2_manual(yt, yp)
    print(f"\n  sklearn r2_score(yt, yp)     = {r2_sk:.6f}")
    print(f"  manual 1 - SS_res/SS_tot     = {r2_man:.6f}")
    print(f"  match: {np.isclose(r2_sk, r2_man, rtol=1e-5)}")

    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - np.mean(yt)) ** 2))
    print(f"  SS_res={ss_res:.4f}  SS_tot={ss_tot:.4f}")

    print("\n" + "=" * 72)
    print("4) ACTUAL vs PREDICTED (test set) - saving plot")
    print("=" * 72)
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(yt, yp, alpha=0.35, s=12, label="points")
        lo = min(yt.min(), yp.min())
        hi = max(yt.max(), yp.max())
        ax.plot([lo, hi], [lo, hi], "r--", lw=1, label="perfect")
        ax.set_xlabel("Actual WQI (test)")
        ax.set_ylabel("Predicted WQI (test)")
        ax.set_title("LSTM test set: actual vs predicted (flattened horizons)")
        ax.legend()
        ax.set_aspect("equal", adjustable="box")
        args.plot.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.plot, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: {args.plot.resolve()}")
    except ImportError:
        print("  matplotlib not installed - skip plot. pip install matplotlib")

    _print_causes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
