-- ─────────────────────────────────────────────────────────────────────────────
-- finance_queries.sql — Named SQL queries used by the Finance ML pipeline
-- ─────────────────────────────────────────────────────────────────────────────

-- get_finance_window: last 90 days of finance data for scoring
-- :name get_finance_window
SELECT
    date,
    revenue,
    expenses,
    profit_margin,
    cash_flow
FROM finance_daily
WHERE date >= DATE('now', '-90 days')
ORDER BY date DESC;


-- get_finance_training_window: last 18 months for model training
-- :name get_finance_training_window
SELECT
    date,
    revenue,
    expenses,
    profit_margin,
    cash_flow,
    anomaly_flag
FROM finance_daily
WHERE date >= DATE('now', '-548 days')   -- ~18 months
ORDER BY date ASC;


-- get_finance_anomalies: active anomalies in last 30 days
-- :name get_finance_anomalies
SELECT
    id,
    detected_at,
    domain,
    record_date,
    anomaly_score,
    description,
    severity
FROM anomaly_log
WHERE domain = 'finance'
  AND detected_at >= DATE('now', '-30 days')
ORDER BY detected_at DESC;


-- get_revenue_stats: basic revenue statistics for scoring normalization
-- :name get_revenue_stats
SELECT
    AVG(revenue)    AS avg_revenue,
    MAX(revenue)    AS max_revenue,
    MIN(revenue)    AS min_revenue,
    AVG(profit_margin) AS avg_profit_margin,
    AVG(cash_flow)  AS avg_cash_flow
FROM finance_daily
WHERE date >= DATE('now', '-90 days');
