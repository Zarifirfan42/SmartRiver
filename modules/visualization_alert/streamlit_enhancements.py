"""
Optional Streamlit UI helpers for new SmartRiver enhancements.

These functions are additive and safe:
- They do not modify existing Streamlit pages automatically.
- You can import and call them in your dashboard where needed.
"""
from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt


def build_actual_vs_predicted_chart(
    actual_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    date_col_actual: str = "date",
    wqi_col_actual: str = "WQI",
):
    """
    Return a matplotlib figure for Actual vs Predicted WQI.
    """
    a = actual_df.copy()
    f = forecast_df.copy()

    if "reading_date" in a.columns and date_col_actual not in a.columns:
        a[date_col_actual] = a["reading_date"]
    if "wqi" in a.columns and wqi_col_actual not in a.columns:
        a[wqi_col_actual] = a["wqi"]

    a[date_col_actual] = pd.to_datetime(a[date_col_actual], errors="coerce")
    f["date"] = pd.to_datetime(f["date"], errors="coerce")
    a = a.dropna(subset=[date_col_actual]).sort_values(date_col_actual)
    f = f.dropna(subset=["date"]).sort_values("date")

    fig, ax = plt.subplots(figsize=(10, 4))
    if len(a) > 0:
        ax.plot(a[date_col_actual], a[wqi_col_actual], label="Actual WQI", linewidth=2)
    if len(f) > 0:
        ax.plot(f["date"], f["predicted_wqi"], label="Predicted WQI", linestyle="--", linewidth=2)
    ax.set_title("Actual vs Predicted WQI")
    ax.set_xlabel("Date")
    ax.set_ylabel("WQI")
    ax.set_ylim(0, 100)
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def render_alert_panel(st, alerts: list[dict], max_items: int = 20):
    """
    Render alert list in Streamlit using existing `st` object.
    """
    st.subheader("Enhanced Alerts")
    if not alerts:
        st.success("No active enhanced alerts.")
        return
    for a in alerts[:max_items]:
        alert_type = a.get("alert_type", "Alert")
        severity = str(a.get("severity", "")).lower()
        station = a.get("station_name", "Unknown")
        date = a.get("date", "-")
        message = a.get("message", "")
        wqi = a.get("wqi", None)
        line = f"[{alert_type}] {station} | {date} | {message}"
        if wqi is not None:
            line += f" (WQI: {float(wqi):.2f})"
        if severity == "high" or (wqi is not None and float(wqi) < 60):
            st.error(line)
        else:
            st.warning(line)


def render_evaluation_panel(st, evaluation: dict):
    """
    Display RMSE, MAE, and optional training loss in Streamlit.
    """
    st.subheader("LSTM Model Evaluation")
    rmse = evaluation.get("rmse")
    mae = evaluation.get("mae")
    c1, c2 = st.columns(2)
    c1.metric("RMSE", "-" if rmse is None else f"{float(rmse):.3f}")
    c2.metric("MAE", "-" if mae is None else f"{float(mae):.3f}")

    train_loss = evaluation.get("train_loss", []) or []
    val_loss = evaluation.get("val_loss", []) or []
    if train_loss:
        st.caption("Training loss trend (lower is better)")
        loss_df = pd.DataFrame({"epoch": list(range(1, len(train_loss) + 1)), "train_loss": train_loss})
        if val_loss:
            loss_df["val_loss"] = val_loss[: len(loss_df)]
        st.line_chart(loss_df.set_index("epoch"))


def render_forecast_explanation(st, explanation: dict):
    """
    Show easy-to-understand forecast interpretation for non-technical users.
    """
    st.subheader("Forecast Explanation")
    st.info(f"Trend: {explanation.get('trend', 'N/A')}")
    st.write(explanation.get("explanation", "No explanation available."))

