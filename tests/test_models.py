"""
tests/test_models.py
────────────────────────────────────────────────────────────────────────────────
Unit tests for all 5 ML models.
Validates output shape, score ranges, anomaly flag types.
"""

import pytest
import numpy as np
import pandas as pd


class TestFinanceAnomalyDetector:
    def test_train_and_predict_shape(self, finance_df_small, config):
        from ml.models.finance_anomaly import FinanceAnomalyDetector
        model = FinanceAnomalyDetector(config)
        model.train(finance_df_small)
        result = model.predict(finance_df_small)
        assert "anomaly_score" in result.columns
        assert "is_anomaly" in result.columns
        assert len(result) == len(finance_df_small)

    def test_is_anomaly_is_boolean(self, finance_df_small, config):
        from ml.models.finance_anomaly import FinanceAnomalyDetector
        model = FinanceAnomalyDetector(config)
        model.train(finance_df_small)
        result = model.predict(finance_df_small)
        assert result["is_anomaly"].dtype == bool

    def test_anomaly_score_is_numeric(self, finance_df_small, config):
        from ml.models.finance_anomaly import FinanceAnomalyDetector
        model = FinanceAnomalyDetector(config)
        model.train(finance_df_small)
        result = model.predict(finance_df_small)
        assert result["anomaly_score"].dtype in (float, np.float64)

    def test_predict_before_train_raises(self, finance_df_small, config):
        from ml.models.finance_anomaly import FinanceAnomalyDetector
        model = FinanceAnomalyDetector(config)
        with pytest.raises(RuntimeError):
            model.predict(finance_df_small)

    def test_evaluate_returns_metrics(self, finance_df_small, config):
        from ml.models.finance_anomaly import FinanceAnomalyDetector
        model = FinanceAnomalyDetector(config)
        model.train(finance_df_small)
        metrics = model.evaluate(finance_df_small)
        assert "precision" in metrics
        assert "recall" in metrics
        assert 0.0 <= metrics["precision"] <= 1.0
        assert 0.0 <= metrics["recall"] <= 1.0


class TestRevenueForecaster:
    def test_train_and_forecast(self, finance_df_small, config):
        from ml.models.revenue_forecast import RevenueForecaster
        model = RevenueForecaster(config)
        model.train(finance_df_small)
        forecast = model.forecast(n_days=7)
        assert isinstance(forecast, list)
        assert len(forecast) > 0
        assert all(isinstance(v, float) for v in forecast)

    def test_forecast_values_positive(self, finance_df_small, config):
        from ml.models.revenue_forecast import RevenueForecaster
        model = RevenueForecaster(config)
        model.train(finance_df_small)
        forecast = model.forecast(n_days=7)
        assert all(v > 0 for v in forecast)

    def test_feature_importance_shape(self, finance_df_small, config):
        from ml.models.revenue_forecast import RevenueForecaster
        model = RevenueForecaster(config)
        model.train(finance_df_small)
        importance = model.get_feature_importance()
        assert len(importance) > 0


class TestAttritionClassifier:
    def test_train_and_predict_risk(self, employees_df_small, snapshots_df_small, config):
        from ml.models.hr_attrition import AttritionClassifier
        model = AttritionClassifier(config)
        model.train(employees_df_small, snapshots_df_small)
        result = model.predict_risk(employees_df_small)
        assert "attrition_probability" in result.columns
        assert len(result) == len(employees_df_small)

    def test_probabilities_in_range(self, employees_df_small, snapshots_df_small, config):
        from ml.models.hr_attrition import AttritionClassifier
        model = AttritionClassifier(config)
        model.train(employees_df_small, snapshots_df_small)
        result = model.predict_risk(employees_df_small)
        assert (result["attrition_probability"] >= 0.0).all()
        assert (result["attrition_probability"] <= 1.0).all()

    def test_feature_importance_available(self, employees_df_small, snapshots_df_small, config):
        from ml.models.hr_attrition import AttritionClassifier
        model = AttritionClassifier(config)
        model.train(employees_df_small, snapshots_df_small)
        importance = model.get_feature_importance()
        assert len(importance) > 0


class TestHRAnomalyDetector:
    def test_train_and_predict(self, snapshots_df_small, config):
        from ml.models.hr_anomaly import HRAnomalyDetector
        # Build aggregated input
        agg = (
            snapshots_df_small.groupby("department")
            .agg(
                monthly_attrition_rate=("attrition_flag", "mean"),
                avg_satisfaction=("satisfaction_score", "mean"),
                avg_absenteeism_rate=("absenteeism_days", "mean"),
            )
            .reset_index()
        )
        model = HRAnomalyDetector(config)
        model.train(agg)
        result = model.predict(agg)
        assert "is_anomaly" in result.columns
        assert len(result) == len(agg)

    def test_is_anomaly_bool(self, snapshots_df_small, config):
        from ml.models.hr_anomaly import HRAnomalyDetector
        agg = (
            snapshots_df_small.groupby("department")
            .agg(
                monthly_attrition_rate=("attrition_flag", "mean"),
                avg_satisfaction=("satisfaction_score", "mean"),
                avg_absenteeism_rate=("absenteeism_days", "mean"),
            )
            .reset_index()
        )
        model = HRAnomalyDetector(config)
        model.train(agg)
        result = model.predict(agg)
        assert result["is_anomaly"].dtype == bool


class TestOpsAnomalyDetector:
    def test_train_and_predict(self, ops_df_small, config):
        from ml.models.ops_anomaly import OpsAnomalyDetector
        model = OpsAnomalyDetector(config)
        model.train(ops_df_small)
        result = model.predict(ops_df_small)
        assert "is_anomaly" in result.columns
        assert len(result) == len(ops_df_small)

    def test_evaluate_returns_metrics(self, ops_df_small, config):
        from ml.models.ops_anomaly import OpsAnomalyDetector
        model = OpsAnomalyDetector(config)
        model.train(ops_df_small)
        metrics = model.evaluate(ops_df_small)
        assert "precision" in metrics
        assert 0.0 <= metrics["precision"] <= 1.0
