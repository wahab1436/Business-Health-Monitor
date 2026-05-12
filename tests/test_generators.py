"""
tests/test_generators.py
────────────────────────────────────────────────────────────────────────────────
Unit tests for all three synthetic data generators.
Validates schema, row counts, anomaly injection rates, and value ranges.
"""

import pytest
import pandas as pd
import numpy as np


class TestFinanceGenerator:
    def test_row_count(self, finance_df_small):
        assert len(finance_df_small) == 60

    def test_schema(self, finance_df_small):
        expected = {"date", "revenue", "expenses", "profit_margin", "cash_flow", "anomaly_flag"}
        assert expected.issubset(set(finance_df_small.columns))

    def test_no_null_values(self, finance_df_small):
        assert finance_df_small.isnull().sum().sum() == 0

    def test_revenue_positive(self, finance_df_small):
        assert (finance_df_small["revenue"] > 0).all()

    def test_expenses_positive(self, finance_df_small):
        assert (finance_df_small["expenses"] > 0).all()

    def test_profit_margin_computed_correctly(self, finance_df_small):
        expected_margin = (
            (finance_df_small["revenue"] - finance_df_small["expenses"])
            / finance_df_small["revenue"] * 100
        )
        pd.testing.assert_series_equal(
            finance_df_small["profit_margin"].round(2),
            expected_margin.round(2),
            check_names=False,
        )

    def test_anomaly_flag_is_boolean(self, finance_df_small):
        assert finance_df_small["anomaly_flag"].dtype in (bool, object, "bool")

    def test_anomaly_rate_approximately_correct(self, finance_df_small):
        rate = finance_df_small["anomaly_flag"].mean()
        # Should be roughly 3% ± 5% margin on small sample
        assert 0.0 <= rate <= 0.20

    def test_reproducible_with_same_seed(self):
        from data.generators.finance_generator import generate_finance_data
        df1 = generate_finance_data(n_days=30, seed=99)
        df2 = generate_finance_data(n_days=30, seed=99)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_differ(self):
        from data.generators.finance_generator import generate_finance_data
        df1 = generate_finance_data(n_days=30, seed=1)
        df2 = generate_finance_data(n_days=30, seed=2)
        assert not df1["revenue"].equals(df2["revenue"])


class TestHRGenerator:
    def test_employee_count(self, employees_df_small):
        assert len(employees_df_small) == 50

    def test_schema(self, employees_df_small):
        expected = {
            "employee_id", "department", "tenure_months", "salary",
            "satisfaction_score", "attrition", "absenteeism_days", "anomaly_flag",
        }
        assert expected.issubset(set(employees_df_small.columns))

    def test_departments_valid(self, employees_df_small):
        valid = {"Engineering", "Sales", "HR", "Finance", "Operations"}
        assert set(employees_df_small["department"].unique()).issubset(valid)

    def test_satisfaction_in_range(self, employees_df_small):
        assert (employees_df_small["satisfaction_score"] >= 1.0).all()
        assert (employees_df_small["satisfaction_score"] <= 5.0).all()

    def test_tenure_positive(self, employees_df_small):
        assert (employees_df_small["tenure_months"] > 0).all()

    def test_salary_positive(self, employees_df_small):
        assert (employees_df_small["salary"] > 0).all()

    def test_attrition_is_binary(self, employees_df_small):
        assert set(employees_df_small["attrition"].astype(int).unique()).issubset({0, 1})

    def test_snapshot_row_count(self, snapshots_df_small, employees_df_small):
        # 50 employees × 6 months = 300 rows
        assert len(snapshots_df_small) == 50 * 6

    def test_snapshot_schema(self, snapshots_df_small):
        expected = {
            "employee_id", "snapshot_date", "department",
            "satisfaction_score", "absenteeism_days", "attrition_flag", "anomaly_flag"
        }
        assert expected.issubset(set(snapshots_df_small.columns))


class TestOpsGenerator:
    def test_row_count(self, ops_df_small):
        assert len(ops_df_small) == 60

    def test_schema(self, ops_df_small):
        expected = {
            "date", "sla_compliance_pct", "ticket_volume",
            "avg_resolution_hours", "system_uptime_pct",
            "efficiency_score", "anomaly_flag"
        }
        assert expected.issubset(set(ops_df_small.columns))

    def test_sla_in_range(self, ops_df_small):
        assert (ops_df_small["sla_compliance_pct"] >= 0).all()
        assert (ops_df_small["sla_compliance_pct"] <= 100).all()

    def test_uptime_in_range(self, ops_df_small):
        assert (ops_df_small["system_uptime_pct"] >= 0).all()
        assert (ops_df_small["system_uptime_pct"] <= 100).all()

    def test_ticket_volume_positive(self, ops_df_small):
        assert (ops_df_small["ticket_volume"] >= 0).all()

    def test_resolution_hours_positive(self, ops_df_small):
        assert (ops_df_small["avg_resolution_hours"] > 0).all()

    def test_efficiency_score_in_range(self, ops_df_small):
        assert (ops_df_small["efficiency_score"] >= 0).all()
        assert (ops_df_small["efficiency_score"] <= 100).all()
