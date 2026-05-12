"""
app/components/anomaly_badge.py
"""

import streamlit as st
import pandas as pd

SEVERITY_STYLES = {
    "high":   {"color": "#ef4444", "bg": "rgba(239,68,68,0.08)",  "border": "rgba(239,68,68,0.25)",  "label": "HIGH"},
    "medium": {"color": "#f59e0b", "bg": "rgba(245,158,11,0.08)", "border": "rgba(245,158,11,0.25)", "label": "MEDIUM"},
    "low":    {"color": "#22c55e", "bg": "rgba(34,197,94,0.08)",  "border": "rgba(34,197,94,0.25)",  "label": "LOW"},
}

DOMAIN_LABELS = {
    "finance":    "Finance",
    "hr":         "HR",
    "operations": "Operations",
}


def render_anomaly_badge(domain, severity, description, detected_at, department=""):
    style = SEVERITY_STYLES.get(severity.lower(), SEVERITY_STYLES["medium"])
    domain_label = DOMAIN_LABELS.get(domain.lower(), domain.upper())
    ts = str(detected_at)[:16].replace("T", " ")

    dept_html = ""
    if department:
        dept_html = (
            '<span style="padding:1px 8px;border-radius:999px;background:rgba(255,255,255,0.05);'
            'border:1px solid rgba(255,255,255,0.08);font-size:10.5px;color:#64748b;">'
            + department + '</span>'
        )

    header = (
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">'
        '<span style="width:7px;height:7px;border-radius:50%;background:' + style["color"] + ';'
        'box-shadow:0 0 6px ' + style["color"] + ';display:inline-block;flex-shrink:0;"></span>'
        '<span style="font-size:10.5px;font-weight:700;color:' + style["color"] + ';'
        'text-transform:uppercase;letter-spacing:0.08em;">' + style["label"] + '</span>'
        '<span style="font-size:11px;font-weight:600;color:#94a3b8;text-transform:uppercase;'
        'letter-spacing:0.05em;">' + domain_label + '</span>'
        + dept_html +
        '<span style="margin-left:auto;font-size:10.5px;color:#475569;">' + ts + '</span>'
        '</div>'
    )

    body = (
        '<p style="margin:0;font-size:13px;color:#cbd5e1;line-height:1.5;">'
        + description + '</p>'
    )

    card = (
        '<div style="background:' + style["bg"] + ';border:1px solid ' + style["border"] + ';'
        'border-left:3px solid ' + style["color"] + ';border-radius:12px;'
        'padding:12px 16px;margin-bottom:8px;">'
        + header + body + '</div>'
    )

    st.markdown(card, unsafe_allow_html=True)


def render_anomaly_list(anomalies_df: pd.DataFrame) -> None:
    if anomalies_df.empty:
        st.markdown(
            '<div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.2);'
            'border-radius:12px;padding:14px 18px;display:flex;align-items:center;gap:10px;">'
            '<span style="width:8px;height:8px;border-radius:50%;background:#22c55e;'
            'box-shadow:0 0 8px #22c55e;display:inline-block;"></span>'
            '<span style="font-size:13px;color:#86efac;font-weight:500;">'
            'No anomalies detected in the last 7 days</span></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<p style="font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;'
        'letter-spacing:0.07em;margin-bottom:10px;">'
        + str(len(anomalies_df)) + ' active event(s)</p>',
        unsafe_allow_html=True,
    )

    for _, row in anomalies_df.iterrows():
        render_anomaly_badge(
            domain=str(row.get("domain", "")),
            severity=str(row.get("severity", "medium")),
            description=str(row.get("description", "No description available.")),
            detected_at=str(row.get("detected_at", "")),
            department=str(row.get("department", "") or ""),
        )


def render_anomaly_summary_badge(count: int, domain: str = "all") -> None:
    color  = "#ef4444" if count > 0 else "#22c55e"
    bg     = "rgba(239,68,68,0.08)" if count > 0 else "rgba(34,197,94,0.08)"
    border = "rgba(239,68,68,0.2)"  if count > 0 else "rgba(34,197,94,0.2)"
    label  = f"{count} anomaly" if count == 1 else f"{count} anomalies"

    st.markdown(
        '<div style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;'
        'border-radius:999px;background:' + bg + ';border:1px solid ' + border + ';'
        'font-size:12px;font-weight:600;color:' + color + ';">'
        '<span style="width:6px;height:6px;border-radius:50%;background:' + color + ';'
        'box-shadow:0 0 5px ' + color + ';display:inline-block;"></span>'
        + label +
        '<span style="color:#475569;font-weight:400;font-size:11px;">(' + domain + ')</span>'
        '</div>',
        unsafe_allow_html=True,
    )
