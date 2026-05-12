"""
app/pages/operations.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from app.db.queries import get_latest_score, get_ops_dashboard_data, get_active_anomalies
from app.components.score_card import render_score_card
from app.components.anomaly_badge import render_anomaly_list
from data.pipeline.db_connection import get_connection


def render() -> None:
    st.title("Operations Health")
    st.markdown(
        '<p style="color:#64748b;font-size:14px;margin-top:-4px;">SLA Compliance, Uptime, Ticket Volume and Incidents</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    conn = get_connection()
    score = get_latest_score(conn)
    if score:
        render_score_card("Operations Health Score", float(score["ops_score"]), band=_band(float(score["ops_score"])))

    ops_df = get_ops_dashboard_data(conn, days=30)
    if ops_df.empty:
        st.warning("No operations data available. Run the pipeline first.")
        conn.close()
        return

    ops_df["date"] = pd.to_datetime(ops_df["date"])

    avg_sla     = round(ops_df["sla_compliance_pct"].mean(), 1)
    avg_uptime  = round(ops_df["system_uptime_pct"].mean(), 2)
    avg_res     = round(ops_df["avg_resolution_hours"].mean(), 1)
    avg_tickets = int(ops_df["ticket_volume"].mean())
    n_incidents = int(ops_df["anomaly_flag"].sum())

    cols = st.columns(5)
    cols[0].metric("Avg SLA Compliance",  f"{avg_sla}%",  delta=f"{avg_sla-95:.1f}% vs target", delta_color="normal")
    cols[1].metric("Avg System Uptime",   f"{avg_uptime}%")
    cols[2].metric("Avg Resolution Time", f"{avg_res}h")
    cols[3].metric("Avg Daily Tickets",   f"{avg_tickets:,}")
    cols[4].metric("Incidents (30d)",     f"{n_incidents}", delta=f"{n_incidents} events", delta_color="inverse")

    st.divider()

    st.markdown("### SLA Compliance Trend — 30 Days")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ops_df["date"], y=ops_df["sla_compliance_pct"],
        mode="lines+markers", name="SLA %",
        line=dict(color="#3b82f6", width=2),
        marker=dict(color=ops_df["anomaly_flag"].map({1:"#ef4444",0:"#3b82f6"}),
                    size=ops_df["anomaly_flag"].map({1:9,0:4})),
    ))
    fig.add_hline(y=95, line_dash="dash", line_color="rgba(34,197,94,0.5)",
                  annotation_text="Target 95%", annotation_font_color="#22c55e", annotation_font_size=11)
    fig.add_hline(y=80, line_dash="dash", line_color="rgba(239,68,68,0.4)",
                  annotation_text="Critical 80%", annotation_font_color="#ef4444", annotation_font_size=11)
    _layout(fig, "SLA Compliance (%)")
    fig.update_yaxes(range=[50, 102])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### System Uptime — 30 Days")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=ops_df["date"], y=ops_df["system_uptime_pct"],
                              mode="lines", name="Uptime %", line=dict(color="#22c55e", width=2),
                              fill="tozeroy", fillcolor="rgba(34,197,94,0.06)"))
    fig2.add_hline(y=99.9, line_dash="dash", line_color="rgba(99,102,241,0.5)",
                   annotation_text="Target 99.9%", annotation_font_color="#a5b4fc", annotation_font_size=11)
    _layout(fig2, "Uptime (%)")
    fig2.update_yaxes(range=[80, 101])
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Ticket Volume vs Resolution Time")
    fig3 = px.scatter(
        ops_df, x="ticket_volume", y="avg_resolution_hours", color="anomaly_flag",
        color_discrete_map={0:"#3b82f6", 1:"#ef4444"},
        labels={"ticket_volume":"Daily Ticket Volume","avg_resolution_hours":"Avg Resolution (h)","anomaly_flag":"Anomaly"},
        hover_data={"date":True},
    )
    fig3.update_layout(
        height=300, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=20, l=50, r=20),
        font=dict(color="#94a3b8"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8")),
    )
    fig3.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig3.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("### Operations Anomaly Events — Last 30 Days")
    anomalies = get_active_anomalies(conn, days=30)
    render_anomaly_list(anomalies[anomalies["domain"] == "operations"])
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
        hovermode="x unified", font=dict(color="#94a3b8"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
