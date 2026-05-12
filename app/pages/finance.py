"""
app/pages/finance.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta

from app.db.queries import (
    get_latest_score, get_finance_chart_data,
    get_revenue_forecast, get_active_anomalies,
)
from app.components.score_card import render_score_card
from app.components.anomaly_badge import render_anomaly_list
from data.pipeline.db_connection import get_connection


def render() -> None:
    st.title("Finance Health")
    st.markdown(
        '<p style="color:#64748b;font-size:14px;margin-top:-4px;">Revenue, Margins, Cash Flow and Forecasts</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    conn = get_connection()
    score = get_latest_score(conn)
    if score:
        render_score_card("Finance Health Score", float(score["finance_score"]),
                          band=_band(float(score["finance_score"])))

    df = get_finance_chart_data(conn, days=90)
    if df.empty:
        st.warning("No finance data available. Run the pipeline first.")
        conn.close()
        return

    df["date"] = pd.to_datetime(df["date"])

    st.markdown("### Revenue vs Expenses — 90 Days")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["revenue"], mode="lines", name="Revenue",
                             line=dict(color="#3b82f6", width=2),
                             fill="tozeroy", fillcolor="rgba(59,130,246,0.06)"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["expenses"], mode="lines", name="Expenses",
                             line=dict(color="#ef4444", width=1.5)))
    anomaly_df = df[df["anomaly_flag"] == 1]
    if not anomaly_df.empty:
        fig.add_trace(go.Scatter(x=anomaly_df["date"], y=anomaly_df["revenue"],
                                 mode="markers", name="Anomaly",
                                 marker=dict(color="#ef4444", size=8, symbol="x")))
    _layout(fig, "USD ($)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Profit Margin Trend")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["date"], y=df["profit_margin"], mode="lines",
                              name="Profit Margin %", line=dict(color="#8b5cf6", width=2),
                              fill="tozeroy", fillcolor="rgba(139,92,246,0.06)"))
    fig2.add_hline(y=0, line_dash="dash", line_color="rgba(239,68,68,0.5)",
                   annotation_text="Break-even", annotation_font_color="#ef4444",
                   annotation_font_size=11)
    _layout(fig2, "Margin (%)")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Cumulative Cash Flow")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df["date"], y=df["cash_flow"], mode="lines", name="Cash Flow",
                              line=dict(color="#22c55e", width=2),
                              fill="tozeroy", fillcolor="rgba(34,197,94,0.06)"))
    fig3.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.3)")
    _layout(fig3, "Cash Flow ($)")
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("### 30-Day Revenue Forecast")
    forecast = get_revenue_forecast(conn)
    if forecast:
        last_date = df["date"].max()
        forecast_dates = [last_date + timedelta(days=i + 1) for i in range(len(forecast))]
        forecast_df = pd.DataFrame({"date": forecast_dates, "forecast": forecast})
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=df["date"].tail(30), y=df["revenue"].tail(30),
                                  mode="lines", name="Actual",
                                  line=dict(color="#3b82f6", width=2)))
        fig4.add_trace(go.Scatter(x=forecast_df["date"], y=forecast_df["forecast"],
                                  mode="lines", name="Forecast",
                                  line=dict(color="#f59e0b", width=2, dash="dash"),
                                  fill="tozeroy", fillcolor="rgba(245,158,11,0.06)"))
        _layout(fig4, "Revenue ($)")
        st.plotly_chart(fig4, use_container_width=True)

        avg_f = sum(forecast) / len(forecast)
        avg_a = df["revenue"].tail(30).mean()
        pct   = (avg_f - avg_a) / avg_a * 100
        sign  = "+" if pct >= 0 else ""
        color_word = "green" if pct >= 0 else "red"
        st.markdown(f"Forecast avg: **${avg_f:,.0f}** ({sign} :{color_word}[{pct:.1f}%] vs last 30-day avg)")
    else:
        st.info("No forecast available. Run the full pipeline to generate revenue forecasts.")

    st.markdown("### Finance Anomaly Events — Last 30 Days")
    fin_anomalies = get_active_anomalies(conn, days=30)
    render_anomaly_list(fin_anomalies[fin_anomalies["domain"] == "finance"])
    conn.close()


def _band(s):
    if s >= 75: return "Healthy"
    if s >= 50: return "At Risk"
    return "Critical"


def _layout(fig, ylab):
    fig.update_layout(
        height=300, yaxis_title=ylab,
        margin=dict(t=20, b=20, l=50, r=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8", size=12)),
        hovermode="x unified", font=dict(color="#94a3b8"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
