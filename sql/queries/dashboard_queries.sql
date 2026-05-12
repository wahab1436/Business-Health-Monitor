-- ─────────────────────────────────────────────────────────────────────────────
-- dashboard_queries.sql — SQL queries used exclusively by Streamlit dashboard
-- ─────────────────────────────────────────────────────────────────────────────

-- get_latest_score: most recent composite health score
-- :name get_latest_score
SELECT
    score_date,
    finance_score,
    hr_score,
    ops_score,
    composite_score,
    score_band,
    delta_vs_prev_day,
    anomaly_penalty
FROM health_scores
ORDER BY score_date DESC
LIMIT 1;


-- get_health_trend: 90-day composite score trend for chart
-- :name get_health_trend
SELECT
    score_date,
    finance_score,
    hr_score,
    ops_score,
    composite_score,
    score_band
FROM health_scores
WHERE score_date >= DATE('now', '-90 days')
ORDER BY score_date ASC;


-- get_active_anomalies: anomalies detected in last 7 days
-- :name get_active_anomalies
SELECT
    id,
    detected_at,
    domain,
    record_date,
    department,
    anomaly_score,
    description,
    severity
FROM anomaly_log
WHERE detected_at >= DATE('now', '-7 days')
ORDER BY severity DESC, detected_at DESC;


-- get_finance_chart_data: revenue, expenses, profit for finance page
-- :name get_finance_chart_data
SELECT
    date,
    revenue,
    expenses,
    profit_margin,
    cash_flow,
    anomaly_flag
FROM finance_daily
WHERE date >= DATE('now', '-90 days')
ORDER BY date ASC;


-- get_hr_dashboard_data: department summary for HR page
-- :name get_hr_dashboard_data
SELECT
    department,
    COUNT(*)                                                         AS total_employees,
    ROUND(AVG(satisfaction_score), 2)                                AS avg_satisfaction,
    SUM(CASE WHEN attrition = 1 THEN 1 ELSE 0 END)                  AS attrited_count,
    ROUND(
        SUM(CASE WHEN attrition = 1 THEN 1.0 ELSE 0.0 END)
        / COUNT(*) * 100, 1
    )                                                                AS attrition_rate_pct,
    SUM(CASE WHEN attrition_probability > 0.65 THEN 1 ELSE 0 END)   AS high_risk_count
FROM hr_employees
GROUP BY department
ORDER BY attrition_rate_pct DESC;


-- get_ops_dashboard_data: SLA + uptime trend for ops page
-- :name get_ops_dashboard_data
SELECT
    date,
    sla_compliance_pct,
    system_uptime_pct,
    ticket_volume,
    avg_resolution_hours,
    efficiency_score,
    anomaly_flag
FROM ops_daily
WHERE date >= DATE('now', '-30 days')
ORDER BY date ASC;


-- get_latest_ai_report: most recent diagnostic report
-- :name get_latest_ai_report
SELECT
    report_date,
    composite_score,
    score_band,
    report_text,
    model_used,
    is_fallback,
    word_count,
    created_at
FROM ai_reports
ORDER BY report_date DESC
LIMIT 1;


-- get_ai_report_history: last 30 reports for history browser
-- :name get_ai_report_history
SELECT
    report_date,
    composite_score,
    score_band,
    word_count,
    is_fallback
FROM ai_reports
ORDER BY report_date DESC
LIMIT 30;
