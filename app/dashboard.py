"""
app/dashboard.py
Business Health Monitor — Streamlit Dashboard Entry Point

Run with:
    streamlit run app/dashboard.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="Business Health Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Business Health Monitor — AI-powered real-time business intelligence.",
    },
)

st.markdown("""
<style>
/* ── Base ── */
html, body, [class*="css"] {
    background-color: #080c14 !important;
    color: #e2e8f0 !important;
}

.block-container {
    padding: 2rem 2.5rem 4rem 2.5rem !important;
    max-width: 1440px !important;
}

/* ── Hide ONLY the default Streamlit footer & header bar ── */
/* #MainMenu { visibility: hidden; } */  ← REMOVE OR COMMENT THIS LINE
footer    { visibility: hidden; }

/* ── DO NOT hide toolbar or collapse button ── */

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.35); border-radius: 99px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0c1118 !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
section[data-testid="stSidebar"] * {
    color: #94a3b8 !important;
}

/* ── Sidebar collapse/expand arrow button ── */
[data-testid="collapsedControl"] {
    background: #0c1118 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 50% !important;
    color: #94a3b8 !important;
}
[data-testid="collapsedControl"]:hover {
    background: rgba(99,102,241,0.2) !important;
    color: #a5b4fc !important;
}

/* ── Hide the auto-generated pages nav Streamlit adds from /pages/ folder ── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Radio nav ── */
div[role="radiogroup"] { gap: 0 !important; }

div[role="radiogroup"] > label {
    display: flex !important;
    align-items: center !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    margin: 2px 10px !important;
    cursor: pointer !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: #64748b !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    transition: all 0.15s ease !important;
}

div[role="radiogroup"] > label:hover {
    background: rgba(99,102,241,0.1) !important;
    color: #e2e8f0 !important;
}

div[role="radiogroup"] > label:has(input:checked) {
    background: rgba(99,102,241,0.15) !important;
    color: #a5b4fc !important;
    font-weight: 600 !important;
    border-color: rgba(99,102,241,0.25) !important;
    box-shadow: inset 3px 0 0 #6366f1 !important;
}

div[role="radiogroup"] input[type="radio"] { display: none !important; }

/* ── Typography ── */
h1 {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: #f1f5f9 !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0.2rem !important;
}

h2, h3 { font-weight: 600 !important; color: #f1f5f9 !important; }

h3 {
    font-size: 0.8rem !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    margin-top: 1.75rem !important;
    margin-bottom: 0.6rem !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.07) !important;
    margin: 1.25rem 0 !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    color: #475569 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #f1f5f9 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 12px !important;
    font-weight: 600 !important;
}

/* ── Buttons ── */
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    color: white !important;
    box-shadow: 0 0 18px rgba(99,102,241,0.3) !important;
}
[data-testid="baseButton-secondary"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
}

/* ── Alerts ── */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}
div[data-testid="stAlert"][kind="info"]    { background: rgba(59,130,246,0.08) !important; border-color: rgba(59,130,246,0.2) !important; }
div[data-testid="stAlert"][kind="success"] { background: rgba(34,197,94,0.08) !important;  border-color: rgba(34,197,94,0.2) !important; }
div[data-testid="stAlert"][kind="warning"] { background: rgba(245,158,11,0.08) !important; border-color: rgba(245,158,11,0.2) !important; }
div[data-testid="stAlert"][kind="error"]   { background: rgba(239,68,68,0.08) !important;  border-color: rgba(239,68,68,0.2) !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    overflow: hidden !important;
}

/* ── Code ── */
code {
    background: rgba(99,102,241,0.1) !important;
    border: 1px solid rgba(99,102,241,0.2) !important;
    border-radius: 4px !important;
    color: #a5b4fc !important;
    font-size: 0.82em !important;
    padding: 1px 5px !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="padding:28px 20px 20px 20px;border-bottom:1px solid rgba(255,255,255,0.07);margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <div style="width:34px;height:34px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
                            border-radius:9px;display:flex;align-items:center;justify-content:center;
                            box-shadow:0 0 16px rgba(99,102,241,0.4);flex-shrink:0;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <rect x="3" y="13" width="4" height="8" rx="1" fill="white" opacity="0.9"/>
                        <rect x="10" y="8" width="4" height="13" rx="1" fill="white"/>
                        <rect x="17" y="3" width="4" height="18" rx="1" fill="white" opacity="0.7"/>
                    </svg>
                </div>
                <div>
                    <p style="font-size:14px;font-weight:700;color:#eef2ff;margin:0;line-height:1.3;">Business Health</p>
                    <p style="font-size:14px;font-weight:700;color:#eef2ff;margin:0;line-height:1.3;">Monitor</p>
                </div>
            </div>
            <p style="font-size:10.5px;color:#334155;margin:0;text-transform:uppercase;letter-spacing:0.06em;font-weight:600;">
                AI-Powered Intelligence
            </p>
        </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        options=["Overview", "Finance", "HR", "Operations", "AI Report"],
        label_visibility="collapsed",
    )

    st.markdown("""
        <div style="padding:20px;margin-top:20px;border-top:1px solid rgba(255,255,255,0.06);">
            <p style="font-size:10px;color:#334155;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.08em;margin:0 0 8px 0;">Stack</p>
            <p style="font-size:11px;color:#475569;line-height:2;margin:0 0 14px 0;">
                Python 3.13 &middot; SQLite / PostgreSQL<br>
                scikit-learn &middot; XGBoost<br>
                Groq API &middot; LLaMA 3<br>
                Streamlit &middot; Plotly
            </p>
            <p style="font-size:10px;color:#334155;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.08em;margin:0 0 6px 0;">Pipeline</p>
            <code style="font-size:10.5px;color:#a5b4fc;background:rgba(99,102,241,0.1);
                         padding:4px 8px;border-radius:5px;border:1px solid rgba(99,102,241,0.2);">
                python run_pipeline.py
            </code>
        </div>
    """, unsafe_allow_html=True)

# ─── Page routing ─────────────────────────────────────────────────────────────
from app.pages import overview, finance, hr, operations, ai_report

if page == "Overview":
    overview.render()
elif page == "Finance":
    finance.render()
elif page == "HR":
    hr.render()
elif page == "Operations":
    operations.render()
elif page == "AI Report":
    ai_report.render()
