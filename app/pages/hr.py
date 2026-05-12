"""
app/pages/hr.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.db.queries import (
    get_latest_score, get_hr_department_summary,
    get_hr_headcount_trend, get_active_anomalies,
)
from app.components.score_card import render_score_card
from app.components.anomaly_badge import render_anomaly_list
from data.pipeline.db_connection import get_connection


def render() -> None:
    st.title("HR Health")
    st.markdown(
        '<p style="color:#64748b;font-size:14px;margin-top:-4px;">Attrition, Satisfaction and Headcount</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    conn = get_connection()
    score = get_latest_score(conn)
    if score:
        render_score_card("HR Health Score", float(score["hr_score"]), band=_band(float(score["hr_score"])))

    dept_df = get_hr_department_summary(conn)
    if dept_df.empty:
        st.warning("No HR data available. Run the pipeline first.")
        conn.close()
        return

    total_employees      = int(dept_df["total_employees"].sum())
    total_high_risk      = int(dept_df["high_risk_count"].sum())
    overall_attrition    = round(dept_df["attrited_count"].sum() / total_employees * 100, 1)
    overall_satisfaction = round(
        (dept_df["avg_satisfaction"] * dept_df["total_employees"]).sum() / total_employees, 2
    )

    cols = st.columns(4)
    cols[0].metric("Total Employees",     f"{total_employees:,}")
    cols[1].metric("Overall Attrition",   f"{overall_attrition}%")
    cols[2].metric("Avg Satisfaction",    f"{overall_satisfaction} / 5.0")
    cols[3].metric("High-Risk Employees", f"{total_high_risk}",
                   delta=f"{total_high_risk} flagged", delta_color="inverse")

    st.divider()

    st.markdown("### Attrition Rate by Department")
    fig = go.Figure(go.Bar(
        x=dept_df["department"], y=dept_df["attrition_rate_pct"],
        text=dept_df["attrition_rate_pct"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside", textfont=dict(color="#94a3b8", size=11),
        marker=dict(
            color=dept_df["attrition_rate_pct"],
            colorscale=[[0, "#22c55e"], [0.5, "#f59e0b"], [1, "#ef4444"]],
            showscale=True,
            colorbar=dict(
                title=dict(text="Attrition %", font=dict(color="#64748b")),
                tickfont=dict(color="#64748b"),
            ),
        ),
    ))
    fig.update_layout(
        height=320, yaxis_title="Attrition Rate (%)",
        yaxis=dict(range=[0, dept_df["attrition_rate_pct"].max() * 1.3],
                   gridcolor="rgba(255,255,255,0.05)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=20, l=50, r=20), font=dict(color="#94a3b8"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Average Satisfaction Score by Department")
    fig2 = go.Figure(go.Bar(
        x=dept_df["department"], y=dept_df["avg_satisfaction"],
        text=dept_df["avg_satisfaction"].apply(lambda x: f"{x:.2f}"),
        textposition="outside", textfont=dict(color="#94a3b8", size=11),
        marker=dict(
            color=dept_df["avg_satisfaction"],
            colorscale=[[0, "#ef4444"], [0.5, "#f59e0b"], [1, "#22c55e"]],
            cmin=1, cmax=5, showscale=True,
            colorbar=dict(
                title=dict(text="Score (1-5)", font=dict(color="#64748b")),
                tickfont=dict(color="#64748b"),
            ),
        ),
    ))
    fig2.add_hline(y=3.5, line_dash="dash", line_color="rgba(148,163,184,0.4)",
                   annotation_text="Target 3.5", annotation_font_color="#64748b",
                   annotation_font_size=11)
    fig2.update_layout(
        height=300, yaxis_title="Avg Satisfaction",
        yaxis=dict(range=[0, 5.5], gridcolor="rgba(255,255,255,0.05)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=20, l=50, r=20), font=dict(color="#94a3b8"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### High-Risk Employee Distribution")
    risk_table = dept_df[["department","total_employees","high_risk_count",
                           "attrition_rate_pct","avg_satisfaction"]].copy()
    risk_table["risk_pct"] = (
        risk_table["high_risk_count"] / risk_table["total_employees"] * 100
    ).round(1)
    risk_table.columns = ["Department","Total","High Risk","Attrition %","Avg Satisfaction","Risk %"]
    st.dataframe(
        risk_table.style.background_gradient(subset=["Attrition %","Risk %"], cmap="RdYlGn_r"),
        use_container_width=True, hide_index=True,
    )

    st.markdown("### Monthly Attrition Trend")
    headcount_df = get_hr_headcount_trend(conn)
    if not headcount_df.empty:
        headcount_df["snapshot_date"] = pd.to_datetime(headcount_df["snapshot_date"])
        monthly_total = (
            headcount_df.groupby("snapshot_date")["monthly_attritions"].sum().reset_index()
        )
        fig3 = go.Figure(go.Bar(
            x=monthly_total["snapshot_date"], y=monthly_total["monthly_attritions"],
            name="Monthly Attritions", marker_color="#8b5cf6", marker_line_width=0,
        ))
        fig3.update_layout(
            height=280, yaxis_title="Employees Left",
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20, l=50, r=20), font=dict(color="#94a3b8"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("### HR Anomaly Events — Last 30 Days")
    anomalies = get_active_anomalies(conn, days=30)
    render_anomaly_list(anomalies[anomalies["domain"] == "hr"])
    conn.close()


def _band(s):
    if s >= 75: return "Healthy"
    if s >= 50: return "At Risk"
    return "Critical"
