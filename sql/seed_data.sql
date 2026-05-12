-- ─────────────────────────────────────────────────────────────────────────────
-- seed_data.sql — Minimal test data for development without running generators
-- Run AFTER schema.sql
-- ─────────────────────────────────────────────────────────────────────────────

-- Finance: 5 days of data
INSERT OR IGNORE INTO finance_daily (date, revenue, expenses, profit_margin, cash_flow, anomaly_flag)
VALUES
    ('2026-01-01', 102000.00, 78500.00, 23.04,  102000.00, 0),
    ('2026-01-02', 98000.00,  81200.00, 17.14,  200000.00, 0),
    ('2026-01-03', 55000.00,  72000.00, -30.91, 245000.00, 1),  -- anomaly: revenue drop
    ('2026-01-04', 105000.00, 77000.00, 26.67,  350000.00, 0),
    ('2026-01-05', 110000.00, 79000.00, 28.18,  460000.00, 0);

-- HR employees: 5 sample employees
INSERT OR IGNORE INTO hr_employees
    (employee_id, department, tenure_months, salary, satisfaction_score,
     attrition, absenteeism_days, anomaly_flag, attrition_probability)
VALUES
    (1, 'Engineering', 36, 9500.00, 4.2, 0, 1, 0, 0.12),
    (2, 'Sales',       12, 6100.00, 2.8, 1, 8, 0, 0.74),
    (3, 'HR',          60, 5400.00, 3.9, 0, 2, 0, 0.18),
    (4, 'Finance',     24, 7000.00, 3.1, 0, 5, 0, 0.45),
    (5, 'Operations',   6, 5600.00, 2.1, 1, 12, 1, 0.88);

-- Ops: 3 days of data
INSERT OR IGNORE INTO ops_daily
    (date, sla_compliance_pct, ticket_volume, avg_resolution_hours,
     system_uptime_pct, efficiency_score, anomaly_flag)
VALUES
    ('2026-01-01', 96.5, 142, 3.2, 99.95, 87.4, 0),
    ('2026-01-02', 94.1, 178, 4.8, 99.80, 83.1, 0),
    ('2026-01-03', 71.0, 420, 18.5, 88.00, 52.3, 1);  -- anomaly: outage

-- Seed health score
INSERT OR IGNORE INTO health_scores
    (score_date, finance_score, hr_score, ops_score, composite_score, score_band, delta_vs_prev_day)
VALUES
    ('2026-01-05', 72.5, 65.0, 78.0, 71.5, 'At Risk', -2.3);

-- Seed anomaly log
INSERT OR IGNORE INTO anomaly_log
    (detected_at, domain, record_date, anomaly_score, description, severity)
VALUES
    ('2026-01-03 08:00:00', 'finance',    '2026-01-03', 0.89, 'Revenue dropped 46% vs baseline', 'high'),
    ('2026-01-03 09:00:00', 'operations', '2026-01-03', 0.94, 'System outage: SLA at 71%, uptime at 88%', 'high');

-- Seed config
INSERT OR IGNORE INTO config (id, finance_weight, hr_weight, ops_weight)
VALUES (1, 0.40, 0.30, 0.30);
