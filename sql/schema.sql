-- ─────────────────────────────────────────────────────────────────────────────
-- Business Health Monitor — Database Schema
-- Compatible with PostgreSQL 16 and SQLite 3
-- Run once to initialize: psql -d business_health -f sql/schema.sql
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Finance daily metrics
CREATE TABLE IF NOT EXISTS finance_daily (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            DATE        NOT NULL UNIQUE,
    revenue         REAL        NOT NULL,
    expenses        REAL        NOT NULL,
    profit_margin   REAL        NOT NULL,   -- (revenue - expenses) / revenue * 100
    cash_flow       REAL        NOT NULL,   -- rolling 30-day cumulative net
    anomaly_flag    INTEGER     NOT NULL DEFAULT 0,  -- 1 = injected anomaly
    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_finance_date ON finance_daily(date);

-- 2. HR employee static table
CREATE TABLE IF NOT EXISTS hr_employees (
    employee_id             INTEGER PRIMARY KEY,
    department              TEXT        NOT NULL,
    tenure_months           INTEGER     NOT NULL,
    salary                  REAL        NOT NULL,
    satisfaction_score      REAL        NOT NULL,
    attrition               INTEGER     NOT NULL DEFAULT 0,  -- 1 = left
    absenteeism_days        INTEGER     NOT NULL DEFAULT 0,
    anomaly_flag            INTEGER     NOT NULL DEFAULT 0,
    attrition_probability   REAL        DEFAULT 0.0,   -- updated by ML model
    created_at              TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hr_dept ON hr_employees(department);

-- 3. HR monthly KPI snapshots
CREATE TABLE IF NOT EXISTS hr_monthly_snapshot (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id         INTEGER     NOT NULL REFERENCES hr_employees(employee_id),
    snapshot_date       DATE        NOT NULL,
    department          TEXT        NOT NULL,
    satisfaction_score  REAL        NOT NULL,
    absenteeism_days    INTEGER     NOT NULL DEFAULT 0,
    attrition_flag      INTEGER     NOT NULL DEFAULT 0,
    anomaly_flag        INTEGER     NOT NULL DEFAULT 0,
    created_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_snap_date ON hr_monthly_snapshot(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snap_emp  ON hr_monthly_snapshot(employee_id);

-- 4. Operations daily metrics
CREATE TABLE IF NOT EXISTS ops_daily (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    date                    DATE    NOT NULL UNIQUE,
    sla_compliance_pct      REAL    NOT NULL,
    ticket_volume           INTEGER NOT NULL,
    avg_resolution_hours    REAL    NOT NULL,
    system_uptime_pct       REAL    NOT NULL,
    efficiency_score        REAL    NOT NULL,
    anomaly_flag            INTEGER NOT NULL DEFAULT 0,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ops_date ON ops_daily(date);

-- 5. Daily composite health scores (written by scoring engine)
CREATE TABLE IF NOT EXISTS health_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    score_date          DATE    NOT NULL UNIQUE,
    finance_score       REAL    NOT NULL,
    hr_score            REAL    NOT NULL,
    ops_score           REAL    NOT NULL,
    composite_score     REAL    NOT NULL,
    score_band          TEXT    NOT NULL,   -- 'Healthy' | 'At Risk' | 'Critical'
    delta_vs_prev_day   REAL    DEFAULT 0.0,
    anomaly_penalty     REAL    DEFAULT 0.0,
    finance_forecast    TEXT,               -- JSON array of 30-day forecast values
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_score_date ON health_scores(score_date);

-- 6. Anomaly log (all detected anomalies across all domains)
CREATE TABLE IF NOT EXISTS anomaly_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    domain          TEXT        NOT NULL,   -- 'finance' | 'hr' | 'operations'
    record_date     DATE,
    department      TEXT,                   -- for HR anomalies
    anomaly_score   REAL,
    is_anomaly      INTEGER     NOT NULL DEFAULT 1,
    description     TEXT,
    severity        TEXT        DEFAULT 'medium'  -- 'low' | 'medium' | 'high'
);

CREATE INDEX IF NOT EXISTS idx_anomaly_domain ON anomaly_log(domain);
CREATE INDEX IF NOT EXISTS idx_anomaly_date   ON anomaly_log(detected_at);

-- 7. AI-generated diagnostic reports
CREATE TABLE IF NOT EXISTS ai_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date     DATE        NOT NULL UNIQUE,
    composite_score REAL        NOT NULL,
    score_band      TEXT        NOT NULL,
    report_text     TEXT        NOT NULL,
    model_used      TEXT        NOT NULL DEFAULT 'llama3-8b-8192',
    is_fallback     INTEGER     NOT NULL DEFAULT 0,  -- 1 = rule-based fallback used
    word_count      INTEGER,
    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- 8. System configuration (single-row table)
CREATE TABLE IF NOT EXISTS config (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    finance_weight          REAL    NOT NULL DEFAULT 0.40,
    hr_weight               REAL    NOT NULL DEFAULT 0.30,
    ops_weight              REAL    NOT NULL DEFAULT 0.30,
    anomaly_penalty         REAL    NOT NULL DEFAULT 5.0,
    max_anomaly_penalty     REAL    NOT NULL DEFAULT 20.0,
    last_updated            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default config if not present
INSERT OR IGNORE INTO config (id, finance_weight, hr_weight, ops_weight)
VALUES (1, 0.40, 0.30, 0.30);
