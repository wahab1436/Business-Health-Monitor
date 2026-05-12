"""
ml/models/ops_anomaly.py
────────────────────────────────────────────────────────────────────────────────
Model 5: Operations Anomaly Detector

Algorithm: Isolation Forest
Purpose: Detect system outage events, SLA drops, and resolution time spikes.
Target: Precision > 0.85, Recall > 0.80
"""

import logging
from datetime import datetime
from typing import Any, Dict

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ml.utils.model_store import save_model, load_model

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "sla_compliance_pct", "avg_resolution_hours",
    "system_uptime_pct", "ticket_volume",
]
MODEL_NAME = "ops_anomaly"


class OpsAnomalyDetector:
    """
    Isolation Forest anomaly detector for daily operations data.

    Methods
    -------
    train(df)
    predict(df)
    evaluate(df)
    write_anomalies_to_db()
    save_model() / load_model()
    """

    def __init__(self, config: Dict):
        params = config["ml"]["ops_anomaly"]
        self.model = IsolationForest(
            n_estimators=params["n_estimators"],
            contamination=params["contamination"],
            bootstrap=params["bootstrap"],
            random_state=params["random_state"],
            n_jobs=-1,
        )
        self.scaler = StandardScaler()
        self._fitted = False

    def train(self, df: pd.DataFrame) -> "OpsAnomalyDetector":
        logger.info(f"Training OpsAnomalyDetector on {len(df)} rows…")
        X = df[FEATURE_COLS].astype(float)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._fitted = True
        logger.info("OpsAnomalyDetector trained.")
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("Call train() first.")

        df = df.copy()
        X = df[FEATURE_COLS].astype(float)
        X_scaled = self.scaler.transform(X)

        scores = self.model.decision_function(X_scaled)
        preds  = self.model.predict(X_scaled)

        df["anomaly_score"] = -scores
        df["is_anomaly"]    = preds == -1
        return df

    def evaluate(self, df: pd.DataFrame) -> Dict[str, float]:
        from sklearn.metrics import precision_score, recall_score, f1_score

        if "is_anomaly" not in df.columns:
            df = self.predict(df)

        y_true = df["anomaly_flag"].astype(int)
        y_pred = df["is_anomaly"].astype(int)

        return {
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall":    round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1":        round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        }

    def write_anomalies_to_db(self, df: pd.DataFrame, conn: Any) -> int:
        anomalies = df[df["is_anomaly"]].copy()
        if anomalies.empty:
            return 0

        rows = []
        for _, row in anomalies.iterrows():
            severity = "high" if row["anomaly_score"] > 0.5 else "medium"
            desc = self._describe(row)
            rows.append((
                datetime.now().isoformat(),
                "operations",
                str(row["date"])[:10],
                None,
                float(row["anomaly_score"]),
                1,
                desc,
                severity,
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
        logger.info(f"Wrote {len(rows)} ops anomalies to anomaly_log.")
        return len(rows)

    @staticmethod
    def _describe(row: pd.Series) -> str:
        parts = []
        if row["sla_compliance_pct"] < 85:
            parts.append(f"SLA at {row['sla_compliance_pct']:.1f}%")
        if row["system_uptime_pct"] < 95:
            parts.append(f"Uptime at {row['system_uptime_pct']:.1f}%")
        if row["avg_resolution_hours"] > 8:
            parts.append(f"Resolution time {row['avg_resolution_hours']:.1f}h")
        return "; ".join(parts) if parts else "Ops statistical outlier"

    def save_model(self) -> None:
        save_model({"model": self.model, "scaler": self.scaler}, MODEL_NAME)

    def load_model(self) -> None:
        artifact = load_model(MODEL_NAME)
        self.model = artifact["model"]
        self.scaler = artifact["scaler"]
        self._fitted = True
