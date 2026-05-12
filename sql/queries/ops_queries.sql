-- ─────────────────────────────────────────────────────────────────────────────
-- ops_queries.sql — Named SQL queries used by the Operations ML pipeline
-- ─────────────────────────────────────────────────────────────────────────────

-- get_ops_window: last 30 days of ops data for scoring
-- :name get_ops_window
SELECT
    date,
    sla_compliance_pct,
    ticket_volume,
    avg_resolution_hours,
    system_uptime_pct,
    efficiency_score
FROM ops_daily
WHERE date >= DATE('now', '-30 days')
ORDER BY date;


-- get_ops_training_window: last 12 months for model training
-- :name get_ops_training_window
SELECT
    date,
    sla_compliance_pct,
    ticket_volume,
    avg_resolution_hours,
    system_uptime_pct,
    efficiency_score,
    anomaly_flag
FROM ops_daily
WHERE date >= DATE('now', '-365 days')
ORDER BY date ASC;


-- get_ops_anomalies: recent operational anomalies
-- :name get_ops_anomalies
SELECT
    id,
    detected_at,
    record_date,
    anomaly_score,
    description,
    severity
FROM anomaly_log
WHERE domain = 'operations'
  AND detected_at >= DATE('now', '-30 days')
ORDER BY detected_at DESC;


-- get_ops_stats: summary stats for scoring normalization
-- :name get_ops_stats
SELECT
    ROUND(AVG(sla_compliance_pct), 2)    AS avg_sla,
    ROUND(AVG(system_uptime_pct), 3)     AS avg_uptime,
    ROUND(AVG(avg_resolution_hours), 2)  AS avg_resolution,
    ROUND(AVG(efficiency_score), 2)      AS avg_efficiency,
    SUM(CASE WHEN anomaly_flag = 1 THEN 1 ELSE 0 END) AS total_anomalies
FROM ops_daily
WHERE date >= DATE('now', '-30 days');
