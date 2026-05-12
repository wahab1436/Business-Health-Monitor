"""
app/components/score_card.py
"""

import streamlit as st

BAND_COLORS = {
    "Healthy":  "#22c55e",
    "At Risk":  "#f59e0b",
    "Critical": "#ef4444",
}
BAND_BG = {
    "Healthy":  "rgba(34,197,94,0.08)",
    "At Risk":  "rgba(245,158,11,0.08)",
    "Critical": "rgba(239,68,68,0.08)",
}
BAND_BORDER = {
    "Healthy":  "rgba(34,197,94,0.25)",
    "At Risk":  "rgba(245,158,11,0.25)",
    "Critical": "rgba(239,68,68,0.25)",
}


def render_score_card(
    title: str,
    score: float,
    band: str = "",
    delta: float = 0.0,
    subtitle: str = "",
    show_gauge: bool = False,
) -> None:
    color  = BAND_COLORS.get(band, "#6b7280")
    bg     = BAND_BG.get(band, "rgba(255,255,255,0.04)")
    border = BAND_BORDER.get(band, "rgba(255,255,255,0.08)")

    delta_color = "#22c55e" if delta >= 0 else "#ef4444"
    delta_bg    = "rgba(34,197,94,0.1)" if delta >= 0 else "rgba(239,68,68,0.1)"
    delta_sign  = "+" if delta > 0 else ""

    # Build HTML pieces safely without nested f-strings
    title_html = (
        '<p style="margin:0 0 6px 0;font-size:11px;color:#64748b;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.08em;">' + title + '</p>'
    )

    score_html = (
        '<span style="font-size:2.8rem;font-weight:800;color:' + color + ';'
        'line-height:1;letter-spacing:-0.03em;">' + f"{score:.1f}" + '</span>'
        '<span style="font-size:1rem;color:#475569;font-weight:400;margin-left:3px;">/100</span>'
    )

    if delta != 0:
        score_html += (
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            'background:' + delta_bg + ';color:' + delta_color + ';font-size:11px;'
            'font-weight:600;margin-left:10px;">'
            + delta_sign + f"{delta:.1f}" + ' vs yesterday</span>'
        )

    score_row_html = (
        '<div style="display:flex;align-items:baseline;flex-wrap:wrap;margin-bottom:8px;">'
        + score_html + '</div>'
    )

    band_html = ""
    if band:
        band_html = (
            '<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
            'background:' + bg + ';border:1px solid ' + border + ';color:' + color + ';'
            'font-size:11px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;">'
            + band + '</span>'
        )

    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            '<p style="margin:8px 0 0 0;font-size:11.5px;color:#64748b;">'
            + subtitle + '</p>'
        )

    card_html = (
        '<div style="background:' + bg + ';border:1px solid ' + border + ';'
        'border-left:3px solid ' + color + ';border-radius:14px;'
        'padding:20px 24px;margin-bottom:16px;">'
        + title_html + score_row_html + band_html + subtitle_html
        + '</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)

    if show_gauge:
        _render_gauge(score, color)


def _render_gauge(score: float, color: str) -> None:
    import plotly.graph_objects as go

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#334155",
                     "tickfont": {"color": "#475569", "size": 10}},
            "bar":  {"color": color, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  50], "color": "rgba(239,68,68,0.08)"},
                {"range": [50, 75], "color": "rgba(245,158,11,0.08)"},
                {"range": [75,100], "color": "rgba(34,197,94,0.08)"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.75,
                "value": score,
            },
        },
        number={"suffix": "/100", "font": {"size": 26, "color": color}},
    ))
    fig.update_layout(
        height=210,
        margin=dict(t=10, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_domain_cards(finance: float, hr: float, ops: float) -> None:
    col1, col2, col3 = st.columns(3)

    def _band(s):
        if s >= 75: return "Healthy"
        if s >= 50: return "At Risk"
        return "Critical"

    with col1:
        render_score_card("Finance Score", finance, band=_band(finance))
    with col2:
        render_score_card("HR Score", hr, band=_band(hr))
    with col3:
        render_score_card("Operations Score", ops, band=_band(ops))
