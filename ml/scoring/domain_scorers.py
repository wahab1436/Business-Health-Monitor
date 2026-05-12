"""
ml/scoring/domain_scorers.py
────────────────────────────────────────────────────────────────────────────────
Domain-level score calculators.
Each normalizes domain KPIs from SQL to a 0-100 scale.
"""

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FinanceScorer:
    """
    Computes a 0-100 Finance Health Score from recent daily finance data.

    Scoring components:
        - Profit margin (weighted 0.40)
        - Revenue trend vs 30-day moving average (weighted 0.35)
        - Cash flow positivity (weighted 0.25)
    """

    def score(self, df: pd.DataFrame) -> float:
        """
        Parameters
        ----------
        df : last 90 days from finance_daily, sorted ascending by date

        Returns
        -------
        float in [0, 100]
        """
        if df.empty:
            logger.warning("FinanceScorer: empty dataframe — returning 50.")
            return 50.0

        # ── Profit margin component ────────────────────────────────────────────
        avg_margin = df["profit_margin"].mean()
        # Map [-20%, 40%] → [0, 100]
        margin_score = np.clip((avg_margin + 20) / 60 * 100, 0, 100)

        # ── Revenue trend component ────────────────────────────────────────────
        if len(df) >= 30:
            recent_rev = df["revenue"].tail(7).mean()
            baseline_rev = df["revenue"].mean()
            trend_ratio = recent_rev / (baseline_rev + 1e-9)
            # 0.7 → 0, 1.0 → 50, 1.3 → 100
            trend_score = np.clip((trend_ratio - 0.70) / 0.60 * 100, 0, 100)
        else:
            trend_score = 50.0

        # ── Cash flow component ────────────────────────────────────────────────
        latest_cf = df["cash_flow"].iloc[-1]
        avg_rev = df["revenue"].mean()
        # Normalize by average revenue: positive CF relative to revenue
        cf_ratio = latest_cf / (avg_rev * len(df) + 1e-9)
        cf_score = np.clip(cf_ratio * 100, 0, 100)

        score = 0.40 * margin_score + 0.35 * trend_score + 0.25 * cf_score
        return float(round(score, 2))


class HRScorer:
    """
    Computes a 0-100 HR Health Score.

    Scoring components:
        - Average employee satisfaction score (weighted 0.35)
        - Attrition rate — inverted (weighted 0.40)
        - Average absenteeism — inverted (weighted 0.25)
    """

    def score(self, emp_df: pd.DataFrame) -> float:
        """
        Parameters
        ----------
        emp_df : hr_employees table

        Returns
        -------
        float in [0, 100]
        """
        if emp_df.empty:
            logger.warning("HRScorer: empty dataframe — returning 50.")
            return 50.0

        # ── Satisfaction: 1-5 scale → 0-100 ──────────────────────────────────
        avg_satisfaction = emp_df["satisfaction_score"].mean()
        satisfaction_score = (avg_satisfaction - 1.0) / 4.0 * 100

        # ── Attrition rate: 0% → 100, 30% → 0 ────────────────────────────────
        attrition_rate = emp_df["attrition"].mean() * 100
        attrition_score = np.clip(100 - (attrition_rate / 30 * 100), 0, 100)

        # ── Absenteeism: 0 days → 100, 15+ days → 0 ──────────────────────────
        avg_absent = emp_df["absenteeism_days"].mean()
        absenteeism_score = np.clip(100 - (avg_absent / 15 * 100), 0, 100)

        # ── High-risk penalty ─────────────────────────────────────────────────
        if "attrition_probability" in emp_df.columns:
            high_risk_pct = (emp_df["attrition_probability"] > 0.65).mean() * 100
            risk_penalty = min(high_risk_pct * 0.5, 20)  # max -20 pts
        else:
            risk_penalty = 0.0

        score = (
            0.35 * satisfaction_score
            + 0.40 * attrition_score
            + 0.25 * absenteeism_score
            - risk_penalty
        )
        return float(round(np.clip(score, 0, 100), 2))


class OpsScorer:
    """
    Computes a 0-100 Operations Health Score.

    Scoring components:
        - SLA compliance (weighted 0.40)
        - System uptime (weighted 0.35)
        - Average resolution time — inverted (weighted 0.25)
    """

    def score(self, df: pd.DataFrame) -> float:
        """
        Parameters
        ----------
        df : last 30 days from ops_daily, sorted ascending

        Returns
        -------
        float in [0, 100]
        """
        if df.empty:
            logger.warning("OpsScorer: empty dataframe — returning 50.")
            return 50.0

        # ── SLA: 70% → 0, 100% → 100 ─────────────────────────────────────────
        avg_sla = df["sla_compliance_pct"].mean()
        sla_score = np.clip((avg_sla - 70) / 30 * 100, 0, 100)

        # ── Uptime: 90% → 0, 100% → 100 ─────────────────────────────────────
        avg_uptime = df["system_uptime_pct"].mean()
        uptime_score = np.clip((avg_uptime - 90) / 10 * 100, 0, 100)

        # ── Resolution time: 1h → 100, 24h → 0 ───────────────────────────────
        avg_res = df["avg_resolution_hours"].mean()
        resolution_score = np.clip(100 - (avg_res - 1) / 23 * 100, 0, 100)

        score = 0.40 * sla_score + 0.35 * uptime_score + 0.25 * resolution_score
        return float(round(score, 2))
