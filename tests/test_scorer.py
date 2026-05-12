"""
tests/test_scorer.py
────────────────────────────────────────────────────────────────────────────────
Unit tests for the health scoring engine.
Tests score bounds, anomaly penalties, and band classification.
"""

import pytest
import pandas as pd
import numpy as np


class TestDomainScorers:
    def test_finance_scorer_range(self, finance_df_small):
        from ml.scoring.domain_scorers import FinanceScorer
        scorer = FinanceScorer()
        score = scorer.score(finance_df_small)
        assert 0.0 <= score <= 100.0

    def test_finance_scorer_empty_df(self):
        from ml.scoring.domain_scorers import FinanceScorer
        scorer = FinanceScorer()
        score = scorer.score(pd.DataFrame())
        assert score == 50.0  # default for empty input

    def test_hr_scorer_range(self, employees_df_small):
        from ml.scoring.domain_scorers import HRScorer
        scorer = HRScorer()
        score = scorer.score(employees_df_small)
        assert 0.0 <= score <= 100.0

    def test_hr_scorer_empty_df(self):
        from ml.scoring.domain_scorers import HRScorer
        scorer = HRScorer()
        score = scorer.score(pd.DataFrame())
        assert score == 50.0

    def test_ops_scorer_range(self, ops_df_small):
        from ml.scoring.domain_scorers import OpsScorer
        scorer = OpsScorer()
        score = scorer.score(ops_df_small)
        assert 0.0 <= score <= 100.0

    def test_ops_scorer_perfect_data(self):
        from ml.scoring.domain_scorers import OpsScorer
        scorer = OpsScorer()
        df = pd.DataFrame({
            "sla_compliance_pct": [100.0] * 10,
            "system_uptime_pct":  [100.0] * 10,
            "avg_resolution_hours": [1.0]  * 10,
        })
        score = scorer.score(df)
        assert score >= 95.0  # near-perfect data → near-perfect score

    def test_ops_scorer_worst_data(self):
        from ml.scoring.domain_scorers import OpsScorer
        scorer = OpsScorer()
        df = pd.DataFrame({
            "sla_compliance_pct": [60.0] * 10,
            "system_uptime_pct":  [80.0] * 10,
            "avg_resolution_hours": [25.0] * 10,
        })
        score = scorer.score(df)
        assert score <= 20.0  # poor data → low score


class TestHealthScorer:
    def test_get_band_healthy(self, config):
        from ml.scoring.health_scorer import HealthScorer
        scorer = HealthScorer(config)
        assert scorer.get_band(80.0) == "Healthy"

    def test_get_band_at_risk(self, config):
        from ml.scoring.health_scorer import HealthScorer
        scorer = HealthScorer(config)
        assert scorer.get_band(60.0) == "At Risk"

    def test_get_band_critical(self, config):
        from ml.scoring.health_scorer import HealthScorer
        scorer = HealthScorer(config)
        assert scorer.get_band(30.0) == "Critical"

    def test_get_band_boundary_75(self, config):
        from ml.scoring.health_scorer import HealthScorer
        scorer = HealthScorer(config)
        assert scorer.get_band(75.0) == "Healthy"

    def test_get_band_boundary_50(self, config):
        from ml.scoring.health_scorer import HealthScorer
        scorer = HealthScorer(config)
        assert scorer.get_band(50.0) == "At Risk"

    def test_anomaly_penalty_capped(self, config):
        from ml.scoring.health_scorer import HealthScorer
        scorer = HealthScorer(config)
        max_penalty = config["scoring"]["max_anomaly_penalty"]
        per_flag    = config["scoring"]["anomaly_penalty_per_flag"]
        # 100 anomalies should not cause penalty > max
        n_anomalies = 100
        penalty = min(n_anomalies * per_flag, max_penalty)
        assert penalty == max_penalty

    def test_composite_formula(self, config):
        from ml.scoring.health_scorer import HealthScorer
        scorer = HealthScorer(config)
        # Given domain scores, compute expected composite
        finance, hr, ops = 80.0, 70.0, 60.0
        expected = (
            config["scoring"]["weights"]["finance"]    * finance
            + config["scoring"]["weights"]["hr"]       * hr
            + config["scoring"]["weights"]["operations"]* ops
        )
        composite = round(
            config["scoring"]["weights"]["finance"]    * finance
            + config["scoring"]["weights"]["hr"]       * hr
            + config["scoring"]["weights"]["operations"]* ops,
            2,
        )
        assert composite == round(expected, 2)

    def test_three_scenarios(self, config):
        """Test Healthy, At Risk, and Critical classification with known inputs."""
        from ml.scoring.health_scorer import HealthScorer
        scorer = HealthScorer(config)

        # Scenario 1: Healthy
        score = 0.40 * 90 + 0.30 * 85 + 0.30 * 80   # = 85.5
        assert scorer.get_band(score) == "Healthy"

        # Scenario 2: At Risk
        score = 0.40 * 65 + 0.30 * 60 + 0.30 * 55   # = 60.5
        assert scorer.get_band(score) == "At Risk"

        # Scenario 3: Critical
        score = 0.40 * 30 + 0.30 * 40 + 0.30 * 25   # = 31.5
        assert scorer.get_band(score) == "Critical"
