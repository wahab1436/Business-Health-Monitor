"""
ml/models/hr_anomaly.py
────────────────────────────────────────────────────────────────────────────────
Model 4: HR Anomaly Detector

Algorithm: Local Outlier Factor (novelty=True)
Purpose: Detect sudden department-level attrition spikes or satisfaction collapses.
Target: Recall > 0.75
"""

import logging
from datetime import datetime
from typing import Any, Dict

import pandas as pd
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from ml.utils.model_store import save_model, load_model

logger = logging.getLogger(__name__)

FEATURE_COLS = ["monthly_attrition_rate", "avg_satisfaction", "avg_absenteeism_rate"]
MODEL_NAME = "hr_anomaly"


class HRAnomalyDetector:
    """
    LOF-based anomaly detector for monthly department-level HR aggregates.

    Methods
    -------
    train(agg_df)            — Fit LOF on historical aggregates
    predict(agg_df)          — Return agg_df with is_anomaly column
    write_anomalies_to_db()
    save_model() / load_model()
    """

    def __init__(self, config: Dict):
        params = config["ml"]["hr_anomaly"]
        self.model = LocalOutlierFactor(
            n_neighbors=params["n_neighbors"],
            contamination=params["contamination"],
            novelty=True,
        )
        self.scaler = StandardScaler()
        self._fitted = False

    def _prepare(self, agg_df: pd.DataFrame) -> pd.DataFrame:
        """Select and fill feature columns."""
        df = agg_df.copy()
        for col in FEATURE_COLS:
            if col not in df.columns:
                df[col] = 0.0
        return df[FEATURE_COLS].fillna(0.0)

    def train(self, agg_df: pd.DataFrame) -> "HRAnomalyDetector":
        """Fit on aggregated HR department-month data."""
        logger.info(f"Training HRAnomalyDetector on {len(agg_df)} aggregates…")
        X = self._prepare(agg_df)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._fitted = True
        logger.info("HRAnomalyDetector trained.")
        return self

    def predict(self, agg_df: pd.DataFrame) -> pd.DataFrame:
        """Predict anomalies in department-month aggregates."""
        if not self._fitted:
            raise RuntimeError("Call train() first.")

        agg_df = agg_df.copy()
        X = self._prepare(agg_df)
        X_scaled = self.scaler.transform(X)

        scores = self.model.decision_function(X_scaled)
        preds  = self.model.predict(X_scaled)

        agg_df["anomaly_score"] = -scores
        agg_df["is_anomaly"]    = preds == -1
        return agg_df

    def write_anomalies_to_db(self, agg_df: pd.DataFrame, conn: Any) -> int:
        anomalies = agg_df[agg_df["is_anomaly"]].copy()
        if anomalies.empty:
            return 0

        rows = []
        for _, row in anomalies.iterrows():
            rows.append((
                datetime.now().isoformat(),
                "hr",
                None,
                str(row.get("department", "")),
                float(row["anomaly_score"]),
                1,
                f"Dept {row.get('department','')} — attrition spike or satisfaction collapse",
                "high" if row["anomaly_score"] > 0.5 else "medium",
            ))

        sql = """
            INSERT INTO anomaly_log
                (detected_at, domain, record_date, department, anomaly_score,
                 is_anomaly, description, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cur = conn.cursor()
        cur.executemany(sql, rows)
        conn.commit()
        logger.info(f"Wrote {len(rows)} HR anomalies to anomaly_log.")
        return len(rows)

    def save_model(self) -> None:
        save_model({"model": self.model, "scaler": self.scaler}, MODEL_NAME)

    def load_model(self) -> None:
        artifact = load_model(MODEL_NAME)
        self.model = artifact["model"]
        self.scaler = artifact["scaler"]
        self._fitted = True
