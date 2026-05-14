"""
LSTM ablation grids (pick with flags).

Default: Config 13 reference + experiments 15–20 (combined best from 15–19 per hyperparameter).

Config 13: seq_len=30, BiLSTM (128, 64), direction_loss_weight=0.30, monsoon, seed=42.

Usage (repo root):
  python -m ml_engine.lstm_ablation --csv sample_water_quality --no-by-river --year-from 2023 --year-to 2025
  python -m ml_engine.lstm_ablation --csv sample_water_quality --no-by-river --config5-grid
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _prep_df(args: argparse.Namespace):
    from data_preprocessing.services.pipeline import ingest_csv, clean_data, impute_missing, add_wqi, feature_engineering
    from ml_engine.train import _collect_training_csv_paths, _filter_by_calendar_years

    paths = _collect_training_csv_paths(Path(args.datasets_dir), args.csv, use_by_river=not args.no_by_river)
    df_raw = ingest_csv(paths[0])
    df_raw = _filter_by_calendar_years(df_raw, args.year_from, args.year_to)
    df_base = clean_data(df_raw, remove_duplicates=True)
    df_base = impute_missing(df_base, strategy="median")
    df_base = add_wqi(df_base)
    df, _ = feature_engineering(df_base, rolling_window=7, lag_days=[1, 7, 14], normalize=True)
    return df


def _r2_sort_key(v: Any) -> float:
    if v is None or (isinstance(v, float) and (math.isnan(v) or not math.isfinite(v))):
        return float("-inf")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("-inf")


def _print_metric_block(m: dict[str, Any]) -> None:
    ex = m.get("regression_extras") or {}
    wb = m.get("wqi_clean_binary_at_81") or {}
    print(
        f"  MSE: {m.get('mse')}  MAE: {m.get('mae')}\n"
        f"  mean_y_true: {ex.get('mean_y_true')}  mean_y_pred: {ex.get('mean_y_pred')}  "
        f"bias(pred-true): {ex.get('mean_bias_pred_minus_true')}\n"
        f"  pearson_r: {ex.get('pearson_r')}  explained_variance: {ex.get('explained_variance')}  "
        f"MAPE%: {ex.get('mape_pct')}  median_ae: {ex.get('median_ae')}\n"
        f"  direction_step_accuracy: {ex.get('direction_step_accuracy')}  "
        f"within_5wqi_points_pct: {ex.get('within_5wqi_points_pct')}\n"
        f"  binary (WQI>=81=clean): accuracy={wb.get('accuracy')}  precision_clean={wb.get('precision_clean_class')}  "
        f"recall_clean={wb.get('recall_clean_class')}  f1_clean={wb.get('f1_clean_class')}"
    )


def _pick_best_key(keys: list[str], by_key: dict[str, dict[str, Any]]) -> str:
    ok = [k for k in keys if k in by_key and by_key[k].get("r2") is not None]
    if not ok:
        return keys[0]
    return max(ok, key=lambda k: _r2_sort_key(by_key[k].get("r2")))


def main() -> int:
    parser = argparse.ArgumentParser(description="LSTM ablation (default: Config 13 + experiments 15–20)")
    parser.add_argument("--datasets-dir", type=Path, default=PROJECT_ROOT / "datasets")
    parser.add_argument("--csv", type=str, required=True)
    parser.add_argument("--no-by-river", action="store_true")
    parser.add_argument("--year-from", type=int, default=None)
    parser.add_argument("--year-to", type=int, default=None)
    parser.add_argument("--lstm-station", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--round1-only",
        action="store_true",
        help="Run original rounds 1–4 only (baseline, seq60, direction, diff)",
    )
    parser.add_argument(
        "--legacy-config3-grid",
        action="store_true",
        help="Run config-3 reference + experiments 5–9",
    )
    parser.add_argument(
        "--config5-grid",
        action="store_true",
        help="Run Config 5 reference + experiments 10–14 (previous phase)",
    )
    args = parser.parse_args()

    from ml_engine.services.forecasting_service import LSTM_EXTRA_RAW_PARAMS_DEFAULT, train as train_lstm

    df = _prep_df(args)

    base_kw = dict(
        station_code=args.lstm_station,
        horizon=7,
        epochs=args.epochs,
        verbose=0,
        loss_plot_path=None,
        pred_plot_path=None,
        seed=args.seed,
        huber_delta=1.0,
        use_wqi_diff=False,
        add_month_cyclical=False,
        use_bidirectional=True,
        extra_param_columns=(),
        lstm_units=(64, 32),
        dropout=0.2,
    )

    config3 = {**base_kw, "seq_len": 30, "direction_loss_weight": 0.15}
    config5 = {**base_kw, "seq_len": 30, "direction_loss_weight": 0.30}
    config13 = {
        **base_kw,
        "seq_len": 30,
        "direction_loss_weight": 0.30,
        "lstm_units": (128, 64),
        "dropout": 0.2,
    }

    experiments: list[tuple[str, str | None, dict]] = []
    # (print_label, merge_key_for_phase3, kwargs) — merge_key only for phase3 first pass

    if args.round1_only:
        experiments = [
            ("1) BASELINE: Huber + level + seq30", None, {**base_kw, "seq_len": 30, "direction_loss_weight": 0.0}),
            ("2) ONLY: seq_len=60", None, {**base_kw, "seq_len": 60, "direction_loss_weight": 0.0}),
            ("3) ONLY: direction_loss_weight=0.15", None, {**base_kw, "seq_len": 30, "direction_loss_weight": 0.15}),
            ("4) ONLY: use_wqi_diff=True", None, {**base_kw, "seq_len": 30, "direction_loss_weight": 0.0, "use_wqi_diff": True}),
        ]
    elif args.legacy_config3_grid:
        experiments = [
            ("3) CONFIG-3 (reference): seq30 + direction 0.15 + BiLSTM + monsoon", None, dict(config3)),
            ("5) Config3 + direction_loss_weight=0.30", None, {**config3, "direction_loss_weight": 0.30}),
            ("6) Config3 + month_sin/cos", None, {**config3, "add_month_cyclical": True}),
            ("7) Config3 + seq_len=14", None, {**config3, "seq_len": 14}),
            ("8) Config3 + unidirectional LSTM", None, {**config3, "use_bidirectional": False}),
            (
                "9) COMBINED: dir=0.30 + month_sin/cos + seq_len=14 + BiLSTM",
                None,
                {**config3, "direction_loss_weight": 0.30, "add_month_cyclical": True, "seq_len": 14, "use_bidirectional": True},
            ),
        ]
    elif args.config5_grid:
        raw_note = "DO, pH, AN (AN = NH3-N)"
        experiments = [
            ("5) CONFIG-5 (reference): seq30 + direction 0.30 + BiLSTM + monsoon", None, dict(config5)),
            ("10) Config5 + direction_loss_weight=0.50", None, {**config5, "direction_loss_weight": 0.50}),
            ("11) Config5 + epochs=100", None, {**config5, "epochs": 100}),
            (f"12) Config5 + extra inputs {raw_note}", None, {**config5, "extra_param_columns": LSTM_EXTRA_RAW_PARAMS_DEFAULT}),
            ("13) Config5 + lstm_units=(128, 64)", None, {**config5, "lstm_units": (128, 64)}),
            ("14) Config5 + direction 0.50 + epochs=100", None, {**config5, "direction_loss_weight": 0.50, "epochs": 100}),
        ]
    else:
        experiments = [
            (
                "13) CONFIG-13 (reference): seq30 + BiLSTM(128,64) + direction 0.30 + monsoon",
                "ref13",
                dict(config13),
            ),
            ("15) Config13 + lstm_units=(256, 128)", "15", {**config13, "lstm_units": (256, 128)}),
            ("16) Config13 + lstm_units=(128, 64, 32) [3 BiLSTM layers]", "16", {**config13, "lstm_units": (128, 64, 32)}),
            ("17) Config13 + direction_loss_weight=0.40", "17", {**config13, "direction_loss_weight": 0.40}),
            ("18) Config13 + seq_len=21", "18", {**config13, "seq_len": 21}),
            ("19) Config13 + dropout=0.1", "19", {**config13, "dropout": 0.1}),
        ]

    print("=" * 76)
    print("SmartRiver LSTM ablation")
    print(f"  seed={args.seed}  default_epochs={args.epochs}  rows={len(df)}")
    print("=" * 76)

    rows_out: list[tuple[str, float | None, float | None, dict[str, Any] | None]] = []
    by_key: dict[str, dict[str, Any]] = {}

    for label, merge_key, kw in experiments:
        out = train_lstm(df, **kw)
        if out.get("error"):
            print(f"\n{label}\n  ERROR: {out['error']}")
            rows_out.append((label, None, None, None))
            continue
        m = out.get("metrics") or {}
        r2 = m.get("r2")
        rmse = m.get("rmse")
        rows_out.append((label, r2, rmse, m))
        r2_s = f"{r2:.6f}" if r2 is not None and isinstance(r2, (int, float)) else str(r2)
        rmse_s = f"{rmse:.6f}" if rmse is not None and isinstance(rmse, (int, float)) else str(rmse)
        print(f"\n{label}\n  R2 (test): {r2_s}\n  RMSE:      {rmse_s}")
        _print_metric_block(m)
        if merge_key:
            by_key[merge_key] = {"label": label, "kw": kw, "r2": r2, "rmse": rmse, "metrics": m}

    if not args.round1_only and not args.legacy_config3_grid and not args.config5_grid:
        needed = {"ref13", "15", "16", "17", "18", "19"}
        if not needed.issubset(by_key.keys()):
            print("\n  [skip 20] Missing some of 13–19 runs (errors above); cannot build combined config.")
        else:
            ku = _pick_best_key(["ref13", "15", "16"], by_key)
            kd = _pick_best_key(["ref13", "17"], by_key)
            ks = _pick_best_key(["ref13", "18"], by_key)
            kdo = _pick_best_key(["ref13", "19"], by_key)
            combined = dict(config13)
            combined["lstm_units"] = by_key[ku]["kw"]["lstm_units"]
            combined["direction_loss_weight"] = by_key[kd]["kw"]["direction_loss_weight"]
            combined["seq_len"] = by_key[ks]["kw"]["seq_len"]
            combined["dropout"] = by_key[kdo]["kw"]["dropout"]
            lu = combined["lstm_units"]
            dw = combined["direction_loss_weight"]
            sl = combined["seq_len"]
            dr = combined["dropout"]
            label20 = (
                "20) COMBINED BEST (per-axis winners from 13–19): "
                f"lstm={lu} (from {ku}), direction={dw} (from {kd}), "
                f"seq_len={sl} (from {ks}), dropout={dr} (from {kdo})"
            )
            print("\n" + "-" * 76)
            print(label20)
            print("-" * 76)
            out20 = train_lstm(df, **combined)
            if out20.get("error"):
                print(f"  ERROR: {out20['error']}")
                rows_out.append((label20, None, None, None))
            else:
                m20 = out20.get("metrics") or {}
                r2 = m20.get("r2")
                rmse = m20.get("rmse")
                rows_out.append((label20, r2, rmse, m20))
                r2_s = f"{r2:.6f}" if r2 is not None and isinstance(r2, (int, float)) else str(r2)
                rmse_s = f"{rmse:.6f}" if rmse is not None and isinstance(rmse, (int, float)) else str(rmse)
                print(f"  R2 (test): {r2_s}\n  RMSE:      {rmse_s}")
                _print_metric_block(m20)

    print("\n" + "=" * 76)
    print("SUMMARY — sorted by R² (descending)")
    print("-" * 76)
    ok = [(lab, r2, rmse, m) for lab, r2, rmse, m in rows_out if r2 is not None and rmse is not None]
    ok.sort(key=lambda t: _r2_sort_key(t[1]), reverse=True)
    for label, r2, rmse, m in ok:
        ex = (m or {}).get("regression_extras") or {}
        wb = (m or {}).get("wqi_clean_binary_at_81") or {}
        mm = m or {}
        mse_v, mae_v = mm.get("mse"), mm.get("mae")
        mse_s = f"{mse_v:.6f}" if isinstance(mse_v, (int, float)) else str(mse_v)
        mae_s = f"{mae_v:.6f}" if isinstance(mae_v, (int, float)) else str(mae_v)
        mt, mp = ex.get("mean_y_true"), ex.get("mean_y_pred")
        mean_s = (
            f"{mt:.4f}/{mp:.4f}" if isinstance(mt, (int, float)) and isinstance(mp, (int, float)) else f"{mt}/{mp}"
        )
        print(
            f"  R2={r2:.6f} RMSE={rmse:.6f} MSE={mse_s} MAE={mae_s}  |  mean_y={mean_s}  "
            f"r={ex.get('pearson_r')}  dir_acc={ex.get('direction_step_accuracy')}  "
            f"acc={wb.get('accuracy')} prec={wb.get('precision_clean_class')} rec={wb.get('recall_clean_class')}  |  {label}"
        )
    bad = [lab for lab, r2, rmse, _ in rows_out if r2 is None or rmse is None]
    for lab in bad:
        print(f"  (skipped)  |  {lab}")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
