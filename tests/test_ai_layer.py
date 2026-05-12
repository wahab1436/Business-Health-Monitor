"""
tests/test_ai_layer.py
────────────────────────────────────────────────────────────────────────────────
Tests for the AI diagnostic layer.
Uses mocked Groq API to avoid real API calls in CI.
"""

import pytest
from unittest.mock import patch, MagicMock


SAMPLE_CONTEXT = {
    "report_date": "2026-01-01",
    "composite_score": 71.5,
    "score_band": "At Risk",
    "finance_score": 68.0,
    "hr_score": 72.0,
    "ops_score": 75.0,
    "delta_vs_prev_day": -2.3,
    "anomaly_penalty": 10.0,
    "active_anomalies": [
        {"domain": "finance", "description": "Revenue dropped 40%", "severity": "high"},
    ],
    "hr_attrition_rate_pct": 18.5,
    "ops_sla_30d_avg": 93.2,
    "ops_uptime_30d_avg": 99.4,
    "finance_avg_revenue_30d": 98_000,
    "finance_avg_margin_30d_pct": 19.5,
    "revenue_forecast_7d": [99000, 101000, 103000, 100000, 102000, 104000, 105000],
}


class TestDiagnosticReporter:
    def test_build_user_prompt_contains_context(self):
        from ml.ai_layer.prompt_templates import build_user_prompt
        prompt = build_user_prompt(SAMPLE_CONTEXT)
        assert "71.5" in prompt
        assert "At Risk" in prompt

    def test_fallback_report_generates_text(self, config):
        from ml.ai_layer.diagnostic import DiagnosticReporter
        reporter = DiagnosticReporter(config)
        report = reporter.fallback_report(SAMPLE_CONTEXT)
        assert isinstance(report, str)
        assert len(report.split()) >= 100  # at least 100 words
        assert "Executive Summary" in report
        assert "Risk Factors" in report or "Risk" in report
        assert "Recommended Actions" in report or "Actions" in report

    def test_fallback_includes_score(self, config):
        from ml.ai_layer.diagnostic import DiagnosticReporter
        reporter = DiagnosticReporter(config)
        report = reporter.fallback_report(SAMPLE_CONTEXT)
        assert "71.5" in report or "72" in report  # composite score

    def test_generate_report_uses_fallback_when_no_api_key(self, config):
        """When GROQ_API_KEY is not set, should use fallback silently."""
        from ml.ai_layer.diagnostic import DiagnosticReporter
        reporter = DiagnosticReporter(config)
        # Ensure no env key
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}):
            text, is_fallback = reporter.generate_report(SAMPLE_CONTEXT)
        assert is_fallback is True
        assert len(text) > 50

    def test_generate_report_with_mocked_groq(self, config, mock_groq_response):
        """When Groq is available, should use AI report."""
        from ml.ai_layer.diagnostic import DiagnosticReporter

        reporter = DiagnosticReporter(config)

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_groq_response
        reporter._client = mock_client

        with patch.dict("os.environ", {"GROQ_API_KEY": "test_key_123"}):
            text, is_fallback = reporter.generate_report(SAMPLE_CONTEXT)

        assert is_fallback is False
        assert "Executive Summary" in text

    def test_write_to_db(self, config, test_db):
        """Report should be persisted to ai_reports table."""
        from ml.ai_layer.diagnostic import DiagnosticReporter
        reporter = DiagnosticReporter(config)
        report_text = reporter.fallback_report(SAMPLE_CONTEXT)
        reporter.write_to_db(report_text, True, SAMPLE_CONTEXT, test_db)

        row = test_db.execute("SELECT * FROM ai_reports WHERE report_date = '2026-01-01'").fetchone()
        assert row is not None
        assert row["is_fallback"] == 1
        assert row["composite_score"] == 71.5
        assert row["word_count"] > 0

    def test_system_prompt_not_empty(self):
        from ml.ai_layer.prompt_templates import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 100
        assert "report" in SYSTEM_PROMPT.lower() or "analyst" in SYSTEM_PROMPT.lower()
