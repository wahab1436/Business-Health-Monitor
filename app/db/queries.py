"""
app/db/queries.py
────────────────────────────────────────────────────────────────────────────────
Python wrapper functions around dashboard SQL queries.
All date arithmetic is done in Python (not SQL) for SQLite compatibility.
"""

import json
import logging
from datetime import date, timedelta
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def _read(conn, sql):
    try:
        return pd.read_sql(sql, conn)
    except Exception as exc:
        logger.warning(f"Query failed: {exc}")
        return pd.DataFrame()


def get_latest_score(conn: Any) -> Optional[dict]:
    df = _read(conn,
        "SELECT score_date, finance_score, hr_score, ops_score, "
        "composite_score, score_band, delta_vs_prev_day, anomaly_penalty "
        "FROM health_scores ORDER BY score_date DESC LIMIT 1"
    )
    return df.iloc[0].to_dict() if not df.empty else None


def get_health_trend(conn: Any, days: int = 90) -> pd.DataFrame:
    cutoff = _days_ago(days)
    return _read(conn,
        f"SELECT score_date, finance_score, hr_score, ops_score, composite_score, score_band "
        f"FROM health_scores WHERE score_date >= '{cutoff}' ORDER BY score_date ASC"
    )


def get_active_anomalies(conn: Any, days: int = 7) -> pd.DataFrame:
    cutoff = _days_ago(days)
    return _read(conn,
        f"SELECT id, detected_at, domain, record_date, department, "
        f"anomaly_score, description, severity "
        f"FROM anomaly_log WHERE detected_at >= '{cutoff}' "
        f"ORDER BY severity DESC, detected_at DESC"
    )


def get_finance_chart_data(conn: Any, days: int = 90) -> pd.DataFrame:
    cutoff = _days_ago(days)
    return _read(conn,
        f"SELECT date, revenue, expenses, profit_margin, cash_flow, anomaly_flag "
        f"FROM finance_daily WHERE date >= '{cutoff}' ORDER BY date ASC"
    )


def get_revenue_forecast(conn: Any) -> list:
    df = _read(conn,
        "SELECT finance_forecast FROM health_scores "
        "WHERE finance_forecast IS NOT NULL ORDER BY score_date DESC LIMIT 1"
    )
    if df.empty or df["finance_forecast"].iloc[0] is None:
        return []
    try:
        return json.loads(df["finance_forecast"].iloc[0])
    except (json.JSONDecodeError, TypeError):
        return []


def get_hr_department_summary(conn: Any) -> pd.DataFrame:
    return _read(conn,
        "SELECT department, "
        "COUNT(*) AS total_employees, "
        "ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction, "
        "SUM(CASE WHEN attrition = 1 THEN 1 ELSE 0 END) AS attrited_count, "
        "ROUND(SUM(CASE WHEN attrition = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 1) AS attrition_rate_pct, "
        "SUM(CASE WHEN attrition_probability > 0.65 THEN 1 ELSE 0 END) AS high_risk_count "
        "FROM hr_employees GROUP BY department ORDER BY attrition_rate_pct DESC"
    )


def get_hr_headcount_trend(conn: Any) -> pd.DataFrame:
    return _read(conn,
        "SELECT snapshot_date, department, "
        "COUNT(*) AS headcount, "
        "SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END) AS monthly_attritions "
        "FROM hr_monthly_snapshot GROUP BY snapshot_date, department ORDER BY snapshot_date ASC"
    )


def get_ops_dashboard_data(conn: Any, days: int = 30) -> pd.DataFrame:
    cutoff = _days_ago(days)
    return _read(conn,
        f"SELECT date, sla_compliance_pct, system_uptime_pct, ticket_volume, "
        f"avg_resolution_hours, efficiency_score, anomaly_flag "
        f"FROM ops_daily WHERE date >= '{cutoff}' ORDER BY date ASC"
    )


def get_latest_ai_report(conn: Any) -> Optional[dict]:
    df = _read(conn,
        "SELECT report_date, composite_score, score_band, report_text, "
        "model_used, is_fallback, word_count, created_at "
        "FROM ai_reports ORDER BY report_date DESC LIMIT 1"
    )
    return df.iloc[0].to_dict() if not df.empty else None


def get_ai_report_history(conn: Any, limit: int = 30) -> pd.DataFrame:
    return _read(conn,
        f"SELECT report_date, composite_score, score_band, word_count, is_fallback "
        f"FROM ai_reports ORDER BY report_date DESC LIMIT {limit}"
    )
