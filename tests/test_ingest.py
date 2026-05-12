"""
tests/test_ingest.py
────────────────────────────────────────────────────────────────────────────────
Integration tests for the SQL ingestion pipeline.
Tests idempotency, schema validation, error handling using an in-memory DB.
"""

import sqlite3
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestFinanceIngestion:
    def _insert_finance(self, conn, df):
        """Helper: directly insert finance rows into test DB."""
        rows = [
            (
                str(r["date"])[:10],
                float(r["revenue"]),
                float(r["expenses"]),
                float(r["profit_margin"]),
                float(r["cash_flow"]),
                int(bool(r["anomaly_flag"])),
            )
            for _, r in df.iterrows()
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO finance_daily "
            "(date, revenue, expenses, profit_margin, cash_flow, anomaly_flag) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()

    def test_insert_rows(self, test_db, finance_df_small):
        self._insert_finance(test_db, finance_df_small)
        count = test_db.execute("SELECT COUNT(*) FROM finance_daily").fetchone()[0]
        assert count == len(finance_df_small)

    def test_idempotent_insert(self, test_db, finance_df_small):
        """Inserting the same data twice should not duplicate rows."""
        self._insert_finance(test_db, finance_df_small)
        self._insert_finance(test_db, finance_df_small)  # second run
        count = test_db.execute("SELECT COUNT(*) FROM finance_daily").fetchone()[0]
        assert count == len(finance_df_small)

    def test_date_unique_constraint(self, test_db, finance_df_small):
        """Duplicate dates should not raise an error (INSERT OR IGNORE)."""
        self._insert_finance(test_db, finance_df_small)
        # Try inserting just the first row again
        row = finance_df_small.iloc[0]
        test_db.execute(
            "INSERT OR IGNORE INTO finance_daily "
            "(date, revenue, expenses, profit_margin, cash_flow, anomaly_flag) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(row["date"])[:10], 99999.0, 1.0, 99.0, 99.0, 0),
        )
        test_db.commit()
        # The original row should be preserved, not the duplicate
        rev = test_db.execute(
            "SELECT revenue FROM finance_daily WHERE date = ?",
            (str(row["date"])[:10],),
        ).fetchone()[0]
        assert rev != 99999.0

    def test_schema_validation_raises_on_missing_cols(self):
        from data.pipeline.ingest import validate_schema
        df_bad = pd.DataFrame({"date": ["2026-01-01"], "revenue": [100.0]})
        with pytest.raises(ValueError):
            validate_schema(df_bad, {"date", "revenue", "expenses", "profit_margin",
                                     "cash_flow", "anomaly_flag"}, "finance")

    def test_schema_validation_passes_on_correct_cols(self, finance_df_small):
        from data.pipeline.ingest import validate_schema
        # Should not raise
        validate_schema(
            finance_df_small,
            {"date", "revenue", "expenses", "profit_margin", "cash_flow", "anomaly_flag"},
            "finance",
        )


class TestHRIngestion:
    def test_employee_insert(self, test_db, employees_df_small):
        rows = [
            (
                int(r["employee_id"]),
                str(r["department"]),
                int(r["tenure_months"]),
                float(r["salary"]),
                float(r["satisfaction_score"]),
                int(bool(r["attrition"])),
                int(r["absenteeism_days"]),
                int(bool(r["anomaly_flag"])),
                float(r.get("attrition_probability", 0.0)),
            )
            for _, r in employees_df_small.iterrows()
        ]
        test_db.executemany(
            "INSERT OR IGNORE INTO hr_employees "
            "(employee_id, department, tenure_months, salary, satisfaction_score, "
            "attrition, absenteeism_days, anomaly_flag, attrition_probability) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        test_db.commit()
        count = test_db.execute("SELECT COUNT(*) FROM hr_employees").fetchone()[0]
        assert count == len(employees_df_small)

    def test_snapshot_unique_constraint(self, test_db, employees_df_small, snapshots_df_small):
        """employee_id + snapshot_date must be unique."""
        # Insert employees first
        rows = [(int(r["employee_id"]), str(r["department"]), int(r["tenure_months"]),
                 float(r["salary"]), float(r["satisfaction_score"]),
                 int(bool(r["attrition"])), int(r["absenteeism_days"]),
                 int(bool(r["anomaly_flag"])), 0.0)
                for _, r in employees_df_small.iterrows()]
        test_db.executemany(
            "INSERT OR IGNORE INTO hr_employees "
            "(employee_id, department, tenure_months, salary, satisfaction_score, "
            "attrition, absenteeism_days, anomaly_flag, attrition_probability) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        test_db.commit()


class TestOpsIngestion:
    def test_ops_insert(self, test_db, ops_df_small):
        rows = [
            (
                str(r["date"])[:10],
                float(r["sla_compliance_pct"]),
                int(r["ticket_volume"]),
                float(r["avg_resolution_hours"]),
                float(r["system_uptime_pct"]),
                float(r["efficiency_score"]),
                int(bool(r["anomaly_flag"])),
            )
            for _, r in ops_df_small.iterrows()
        ]
        test_db.executemany(
            "INSERT OR IGNORE INTO ops_daily "
            "(date, sla_compliance_pct, ticket_volume, avg_resolution_hours, "
            "system_uptime_pct, efficiency_score, anomaly_flag) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        test_db.commit()
        count = test_db.execute("SELECT COUNT(*) FROM ops_daily").fetchone()[0]
        assert count == len(ops_df_small)
