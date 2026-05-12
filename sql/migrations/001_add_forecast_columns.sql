-- Migration 001: Add forecast columns to health_scores
-- Run with: psql -d business_health -f sql/migrations/001_add_forecast_columns.sql

-- Add JSON forecast array column if it doesn't already exist
-- PostgreSQL syntax:
-- ALTER TABLE health_scores ADD COLUMN IF NOT EXISTS finance_forecast TEXT;

-- SQLite-compatible (no IF NOT EXISTS for ALTER TABLE):
ALTER TABLE health_scores ADD COLUMN finance_forecast TEXT;
ALTER TABLE health_scores ADD COLUMN hr_risk_headcount INTEGER DEFAULT 0;
ALTER TABLE health_scores ADD COLUMN ops_incident_count INTEGER DEFAULT 0;
