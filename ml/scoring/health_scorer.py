"""
ml/scoring/health_scorer.py
────────────────────────────────────────────────────────────────────────────────
Model 6: Business Health Scoring Engine

Algorithm: Weighted composite scoring (custom Python)
Formula:   Health = (0.40 * Finance) + (0.30 * HR) + (0.30 * Ops) − anomaly_penalties
Output:    Composite score [0-100] + band (Healthy / At Risk / Critical)
"""

import json
import logging
import sqlite3
from datetime import date, timedelta
from typing import Any, Dict

import pandas as pd
import numpy as np

from .domain_scorers import FinanceScorer, HRScorer, OpsScorer

logger = logging.getLogger(__name__)


def _read(conn, sql, params=None):
    """Safe pd.read_sql wrapper — works with both sqlite3 and psycopg2."""
    try:
        if params:
            return pd.read_sql(sql, conn, params=params)
        return pd.read_sql(sql, conn)
    except Exception as exc:
        logger.warning(f"Query failed: {exc}\nSQL: {sql}")
        return pd.DataFrame()


class HealthScorer:
    def __init__(self, config: Dict):
        weights = config["scoring"]["weights"]
        self.w_finance = weights["finance"]
        self.w_hr      = weights["hr"]
        self.w_ops     = weights["operations"]

        self.anomaly_penalty = config["scoring"]["anomaly_penalty_per_flag"]
        self.max_penalty     = config["scoring"]["max_anomaly_penalty"]
        self.bands           = config["scoring"]["bands"]

        self.finance_scorer = FinanceScorer()
        self.hr_scorer      = HRScorer()
        self.ops_scorer     = OpsScorer()

    def run(self, conn: Any) -> Dict:
        today      = date.today()
        day90_ago  = (today - timedelta(days=90)).isoformat()
        day30_ago  = (today - timedelta(days=30)).isoformat()
        day1_ago   = (today - timedelta(days=1)).isoformat()

        # ── Load domain data ──────────────────────────────────────────────────
        finance_df = _read(conn,
            f"SELECT * FROM finance_daily WHERE date >= '{day90_ago}' ORDER BY date"
        )
        emp_df = _read(conn, "SELECT * FROM hr_employees")
        ops_df = _read(conn,
            f"SELECT * FROM ops_daily WHERE date >= '{day30_ago}' ORDER BY date"
        )
        anomalies_df = _read(conn,
            f"SELECT * FROM anomaly_log WHERE detected_at >= '{day1_ago}'"
        )

        logger.info(
            f"Scoring data loaded — finance:{len(finance_df)} hr:{len(emp_df)} "
            f"ops:{len(ops_df)} anomalies:{len(anomalies_df)}"
        )

        # ── Domain scores ──────────────────────────────────────────────────────
        finance_score = self.finance_scorer.score(finance_df)
        hr_score      = self.hr_scorer.score(emp_df)
        ops_score     = self.ops_scorer.score(ops_df)

        # ── Anomaly penalty ───────────────────────────────────────────────────
        penalty = min(len(anomalies_df) * self.anomaly_penalty, self.max_penalty)

        # ── Composite ─────────────────────────────────────────────────────────
        composite = (
            self.w_finance * finance_score
            + self.w_hr    * hr_score
            + self.w_ops   * ops_score
            - penalty
        )
        composite = float(np.clip(composite, 0, 100))
        band      = self.get_band(composite)

        # ── Delta vs previous day ─────────────────────────────────────────────
        prev = _read(conn,
            "SELECT composite_score FROM health_scores ORDER BY score_date DESC LIMIT 1"
        )
        delta = composite - float(prev["composite_score"].iloc[0]) if not prev.empty else 0.0

        result = {
            "finance":   round(finance_score, 2),
            "hr":        round(hr_score, 2),
            "ops":       round(ops_score, 2),
            "composite": round(composite, 2),
            "band":      band,
            "delta":     round(delta, 2),
            "penalty":   round(penalty, 2),
        }

        self.write_to_db(result, conn)
        logger.info(f"Score written: {result}")
        return result

    def get_band(self, score: float) -> str:
        if score >= self.bands["green"]["min"]:
            return "Healthy"
        elif score >= self.bands["yellow"]["min"]:
            return "At Risk"
        return "Critical"

    def write_to_db(self, result: Dict, conn: Any) -> None:
        today = date.today().isoformat()

        if isinstance(conn, sqlite3.Connection):
            conn.execute(
                "INSERT OR REPLACE INTO health_scores "
                "(score_date, finance_score, hr_score, ops_score, composite_score, "
                " score_band, delta_vs_prev_day, anomaly_penalty) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (today, result["finance"], result["hr"], result["ops"],
                 result["composite"], result["band"], result["delta"], result["penalty"]),
            )
            conn.commit()
        else:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO health_scores "
                "(score_date, finance_score, hr_score, ops_score, composite_score, "
                " score_band, delta_vs_prev_day, anomaly_penalty) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (score_date) DO UPDATE SET "
                "finance_score=EXCLUDED.finance_score, hr_score=EXCLUDED.hr_score, "
                "ops_score=EXCLUDED.ops_score, composite_score=EXCLUDED.composite_score, "
                "score_band=EXCLUDED.score_band",
                (today, result["finance"], result["hr"], result["ops"],
                 result["composite"], result["band"], result["delta"], result["penalty"]),
            )
            conn.commit()
        logger.info(f"Health score written: {result['composite']:.1f} ({result['band']})")
