"""
app/pages/overview.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.components.score_card import render_score_card, render_domain_cards
from app.components.anomaly_badge import render_anomaly_list, render_anomaly_summary_badge
from app.db.queries import get_latest_score, get_health_trend, get_active_anomalies
from data.pipeline.db_connection import get_connection


def render() -> None:
    st.title("Business Health Monitor")
    st.markdown(
        '<p style="color:#64748b;font-size:14px;margin-top:-4px;">'
        'Real-time composite intelligence across Finance, HR, and Operations</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    conn = get_connection()
    score = get_latest_score(conn)

    if score is None:
        st.warning("No health scores yet. Run `python run_pipeline.py --mode full` to generate data.")
        conn.close()
        return

    composite = float(score["composite_score"])
    band      = str(score["score_band"])
    delta     = float(score.get("delta_vs_prev_day") or 0)
    penalty   = float(score.get("anomaly_penalty") or 0)

    col_gauge, col_summary = st.columns([1, 2], gap="large")

    with col_gauge:
        render_score_card(
            title="Business Health Score",
            score=composite,
            band=band,
            delta=delta,
            subtitle=f"Anomaly penalty: \u2212{penalty:.1f} pts",
            show_gauge=True,
        )

    with col_summary:
        st.markdown("### Domain Breakdown")
        render_domain_cards(
            finance=float(score["finance_score"]),
            hr=float(score["hr_score"]),
            ops=float(score["ops_score"]),
        )

        st.markdown("### Active Alerts")
        anomalies = get_active_anomalies(conn, days=7)
        fin_count = len(anomalies[anomalies["domain"] == "finance"])
        hr_count  = len(anomalies[anomalies["domain"] == "hr"])
        ops_count = len(anomalies[anomalies["domain"] == "operations"])

        cols = st.columns(3)
        with cols[0]:
            render_anomaly_summary_badge(fin_count, "Finance")
        with cols[1]:
            render_anomaly_summary_badge(hr_count, "HR")
        with cols[2]:
            render_anomaly_summary_badge(ops_count, "Operations")

    st.divider()

    st.markdown("### 90-Day Health Score Trend")
    trend_df = get_health_trend(conn, days=90)

    if not trend_df.empty:
        trend_df["score_date"] = pd.to_datetime(trend_df["score_date"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_df["score_date"], y=trend_df["composite_score"],
            mode="lines", name="Composite",
            line=dict(color="#6366f1", width=2.5),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.07)",
        ))
        fig.add_trace(go.Scatter(
            x=trend_df["score_date"], y=trend_df["finance_score"],
            mode="lines", name="Finance",
            line=dict(color="#3b82f6", width=1.5, dash="dot"),
        ))
        fig.add_trace(go.Scatter(
            x=trend_df["score_date"], y=trend_df["hr_score"],
            mode="lines", name="HR",
            line=dict(color="#8b5cf6", width=1.5, dash="dot"),
        ))
        fig.add_trace(go.Scatter(
            x=trend_df["score_date"], y=trend_df["ops_score"],
            mode="lines", name="Operations",
            line=dict(color="#f59e0b", width=1.5, dash="dot"),
        ))
        fig.add_hline(y=75, line_dash="dash", line_color="rgba(34,197,94,0.35)",
                      annotation_text="Healthy (75)", annotation_font_color="#22c55e",
                      annotation_font_size=11)
        fig.add_hline(y=50, line_dash="dash", line_color="rgba(239,68,68,0.35)",
                      annotation_text="Critical (50)", annotation_font_color="#ef4444",
                      annotation_font_size=11)
        fig.update_layout(
            height=340,
            yaxis=dict(range=[0, 105], gridcolor="rgba(255,255,255,0.05)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8", size=12)),
            margin=dict(t=30, b=20, l=40, r=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
            font=dict(color="#94a3b8"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough score history to display trend chart.")

    st.divider()

    st.markdown("### Recent Anomaly Events (Last 7 Days)")
    render_anomaly_list(anomalies)

    conn.close()
