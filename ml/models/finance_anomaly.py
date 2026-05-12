"""
ml/models/finance_anomaly.py
────────────────────────────────────────────────────────────────────────────────
Model 1: Finance Anomaly Detector

Algorithm: Isolation Forest
Purpose: Detect unusual revenue drops, expense spikes, or cash flow irregularities.
Target: Precision > 0.85, Recall > 0.80 (evaluated against injected anomaly_flag)
"""

import logging
from datetime import datetime
from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ml.utils.model_store import save_model, load_model, model_exists

logger = logging.getLogger(__name__)

FEATURE_COLS = ["revenue", "expenses", "profit_margin", "cash_flow"]
MODEL_NAME = "finance_anomaly"


class FinanceAnomalyDetector:
    """
    Isolation Forest anomaly detector for daily finance data.

    Methods
    -------
    train(df)               — Fit scaler + IsolationForest on df
    predict(df)             — Return df with anomaly_score + is_anomaly columns
    evaluate(df)            — Precision/Recall against ground-truth anomaly_flag
    write_anomalies_to_db() — Persist detected anomalies to anomaly_log table
    save_model()            — Persist fitted model to disk
    load_model()            — Load model from disk
    """

    def __init__(self, config: Dict):
        params = config["ml"]["finance_anomaly"]
        self.model = IsolationForest(
            n_estimators=params["n_estimators"],
            contamination=params["contamination"],
            max_samples=params["max_samples"],
            random_state=params["random_state"],
            n_jobs=-1,
        )
        self.scaler = StandardScaler()
        self._fitted = False

    def train(self, df: pd.DataFrame) -> "FinanceAnomalyDetector":
        """Fit scaler and Isolation Forest on finance_daily data."""
        logger.info(f"Training FinanceAnomalyDetector on {len(df)} rows…")
        X = df[FEATURE_COLS].astype(float)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._fitted = True
        logger.info("FinanceAnomalyDetector trained.")
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict anomalies on the full finance dataset.

        Returns df with two new columns:
            anomaly_score : raw isolation forest decision score (higher = more normal)
            is_anomaly    : bool (True = anomaly detected)
        """
        if not self._fitted:
            raise RuntimeError("Call train() before predict().")

        df = df.copy()
        X = df[FEATURE_COLS].astype(float)
        X_scaled = self.scaler.transform(X)

        # decision_function: negative = anomalous
        scores = self.model.decision_function(X_scaled)
        predictions = self.model.predict(X_scaled)  # -1 = anomaly, 1 = normal

        df["anomaly_score"] = -scores          # flip so higher = more anomalous
        df["is_anomaly"] = predictions == -1
        return df

    def evaluate(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute Precision and Recall against ground-truth anomaly_flag column.
        Requires anomaly_flag and is_anomaly columns in df.
        """
        from sklearn.metrics import precision_score, recall_score, f1_score

        if "is_anomaly" not in df.columns:
            df = self.predict(df)

        y_true = df["anomaly_flag"].astype(int)
        y_pred = df["is_anomaly"].astype(int)

        results = {
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall":    round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1":        round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        }
        logger.info(f"Finance anomaly evaluation: {results}")
        return results

    def write_anomalies_to_db(self, df: pd.DataFrame, conn: Any) -> int:
        """Write detected anomaly rows to the anomaly_log table."""
        anomalies = df[df["is_anomaly"]].copy()
        if anomalies.empty:
            logger.info("No finance anomalies to write.")
            return 0

        rows = []
        for _, row in anomalies.iterrows():
            rows.append((
                datetime.now().isoformat(),
                "finance",
                str(row["date"])[:10],
                None,                              # department (N/A for finance)
                float(row["anomaly_score"]),
                1,
                self._describe_anomaly(row),
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
        logger.info(f"Wrote {len(rows)} finance anomalies to anomaly_log.")
        return len(rows)

    @staticmethod
    def _describe_anomaly(row: pd.Series) -> str:
        desc_parts = []
        if row["revenue"] < 70_000:
            desc_parts.append(f"Revenue low at ${row['revenue']:,.0f}")
        if row["profit_margin"] < 0:
            desc_parts.append(f"Negative profit margin ({row['profit_margin']:.1f}%)")
        if not desc_parts:
            desc_parts.append("Statistical outlier detected by Isolation Forest")
        return "; ".join(desc_parts)

    def save_model(self) -> None:
        save_model({"model": self.model, "scaler": self.scaler}, MODEL_NAME)

    def load_model(self) -> None:
        artifact = load_model(MODEL_NAME)
        self.model = artifact["model"]
        self.scaler = artifact["scaler"]
        self._fitted = True
