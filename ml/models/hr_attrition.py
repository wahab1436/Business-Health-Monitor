"""
ml/models/hr_attrition.py
────────────────────────────────────────────────────────────────────────────────
Model 3: HR Attrition Classifier

Algorithm: Random Forest Classifier
Purpose: Predict which employees are at high attrition risk in next 90 days.
Target: ROC-AUC > 0.82, F1 > 0.78 (weighted)
"""

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from ml.utils.model_store import save_model, load_model

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "tenure_months", "satisfaction_score", "salary_percentile",
    "absenteeism_days", "department_encoded",
]
MODEL_NAME = "hr_attrition"


class AttritionClassifier:
    """
    Random Forest attrition risk classifier.

    Methods
    -------
    train(emp_df, snap_df)   — Build features, stratified split, fit RF
    predict_risk(emp_df)     — Add attrition_probability to emp_df
    get_feature_importance() — Return ranked feature importances
    write_risk_scores_to_db()
    save_model() / load_model()
    """

    def __init__(self, config: Dict):
        params = config["ml"]["hr_attrition"]
        self.model = RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            class_weight=params["class_weight"],
            random_state=params["random_state"],
            n_jobs=-1,
        )
        self.risk_threshold = params["risk_threshold"]
        self.dept_encoder = LabelEncoder()
        self._fitted = False

    def _build_features(self, emp_df: pd.DataFrame) -> pd.DataFrame:
        """Construct the ML feature matrix from the employees table."""
        df = emp_df.copy()

        # Salary percentile within department
        df["salary_percentile"] = df.groupby("department")["salary"].rank(pct=True)

        # Encode department
        df["department_encoded"] = self.dept_encoder.transform(
            df["department"].astype(str)
        )
        return df

    def train(self, emp_df: pd.DataFrame, snap_df: pd.DataFrame) -> "AttritionClassifier":
        """
        Build features from emp_df + snap_df joined on employee_id.
        Fit a Random Forest classifier with stratified 80/20 split.
        """
        logger.info(f"Training AttritionClassifier on {len(emp_df)} employees…")

        # Fit department encoder on training data
        self.dept_encoder.fit(emp_df["department"].astype(str))

        df = self._build_features(emp_df)
        X = df[FEATURE_COLS].astype(float)
        y = df["attrition"].astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, stratify=y, random_state=42
        )

        self.model.fit(X_train, y_train)
        self._fitted = True

        # Evaluate
        y_prob = self.model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= self.risk_threshold).astype(int)

        auc = roc_auc_score(y_test, y_prob)
        f1  = f1_score(y_test, y_pred, average="weighted", zero_division=0)
        cm  = confusion_matrix(y_test, y_pred)

        logger.info(
            f"Attrition Classifier — ROC-AUC={auc:.4f}, F1={f1:.4f}\n"
            f"Confusion Matrix:\n{cm}"
        )
        return self

    def predict_risk(self, emp_df: pd.DataFrame) -> pd.DataFrame:
        """Return emp_df with attrition_probability column added."""
        if not self._fitted:
            raise RuntimeError("Call train() first.")

        df = self._build_features(emp_df)
        X = df[FEATURE_COLS].astype(float)
        prob = self.model.predict_proba(X)[:, 1]
        emp_df = emp_df.copy()
        emp_df["attrition_probability"] = prob.round(4)
        return emp_df

    def get_feature_importance(self) -> pd.Series:
        return pd.Series(
            self.model.feature_importances_, index=FEATURE_COLS
        ).sort_values(ascending=False)

    def write_risk_scores_to_db(self, emp_df: pd.DataFrame, conn: Any) -> None:
        """Update attrition_probability for every employee in hr_employees."""
        cur = conn.cursor()
        rows = [
            (float(r["attrition_probability"]), int(r["employee_id"]))
            for _, r in emp_df.iterrows()
        ]
        cur.executemany(
            "UPDATE hr_employees SET attrition_probability = ? WHERE employee_id = ?",
            rows,
        )
        conn.commit()
        logger.info(f"Updated attrition_probability for {len(rows)} employees.")

    def save_model(self) -> None:
        save_model({"model": self.model, "dept_encoder": self.dept_encoder,
                    "threshold": self.risk_threshold}, MODEL_NAME)

    def load_model(self) -> None:
        artifact = load_model(MODEL_NAME)
        self.model = artifact["model"]
        self.dept_encoder = artifact["dept_encoder"]
        self.risk_threshold = artifact["threshold"]
        self._fitted = True
