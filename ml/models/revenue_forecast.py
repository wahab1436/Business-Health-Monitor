"""
ml/models/revenue_forecast.py
────────────────────────────────────────────────────────────────────────────────
Model 2: Revenue Forecaster

Algorithm: XGBoost Regressor with time-series lag features
Purpose: Forecast next 30 days of revenue to detect projected underperformance.
Target: MAPE < 8% on holdout 3-month test window.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from ml.utils.model_store import save_model, load_model
from ml.utils.preprocessing import create_lag_features, handle_missing

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "lag_7", "lag_14", "lag_30",
    "rolling_mean_30", "rolling_std_30",
    "day_of_week", "month", "quarter",
]
MODEL_NAME = "revenue_forecast"


class RevenueForecaster:
    """
    XGBoost-based rolling revenue forecaster.

    Methods
    -------
    train(df)                — Walk-forward cross-validation and final fit
    forecast(n_days)         — Generate n-day forecast starting from max date
    evaluate(df)             — RMSE, MAE, MAPE on holdout window
    write_forecast_to_db()   — Write forecast JSON to health_scores table
    save_model() / load_model()
    """

    def __init__(self, config: Dict):
        params = config["ml"]["revenue_forecast"]
        self.model = XGBRegressor(
            n_estimators=params["n_estimators"],
            learning_rate=params["learning_rate"],
            max_depth=params["max_depth"],
            subsample=params["subsample"],
            colsample_bytree=params["colsample_bytree"],
            random_state=params["random_state"],
            n_jobs=-1,
            verbosity=0,
        )
        self.lags: List[int] = params["lag_features"]
        self.horizon: int = params["forecast_horizon"]
        self._fitted = False
        self._last_known_df: pd.DataFrame | None = None

    def _featurize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = create_lag_features(df, target_col="revenue", lags=self.lags, date_col="date")
        df = handle_missing(df, strategy="median")
        return df

    def train(self, df: pd.DataFrame) -> "RevenueForecaster":
        """
        Fit XGBoost on 18-month finance data.
        Uses walk-forward validation: train on first 15 months, validate on last 3.
        Final model is fit on all data.
        """
        logger.info(f"Training RevenueForecaster on {len(df)} rows…")
        df = df.sort_values("date").reset_index(drop=True)
        df = self._featurize(df)
        df = df.dropna(subset=FEATURE_COLS)

        # Walk-forward split: last 90 days = test
        cutoff = df["date"].max() - pd.Timedelta(days=90)
        train_df = df[df["date"] <= cutoff]
        test_df  = df[df["date"] >  cutoff]

        X_train = train_df[FEATURE_COLS]
        y_train = train_df["revenue"]

        self.model.fit(X_train, y_train)

        if not test_df.empty:
            metrics = self._compute_metrics(test_df)
            logger.info(f"Walk-forward metrics: {metrics}")

        # Refit on full data
        self.model.fit(df[FEATURE_COLS], df["revenue"])
        self._last_known_df = df
        self._fitted = True
        logger.info("RevenueForecaster fitted on full dataset.")
        return self

    def forecast(self, n_days: int = 30) -> List[float]:
        """
        Generate an n-day rolling forecast.
        Uses the last known data as seed; predictions are fed back as lag inputs.
        """
        if not self._fitted:
            raise RuntimeError("Call train() first.")

        seed = self._last_known_df.sort_values("date").tail(max(self.lags) + 5).copy()
        forecasts = []

        for i in range(n_days):
            row = self._featurize(seed).tail(1)
            if row[FEATURE_COLS].isna().any().any():
                break
            pred = float(self.model.predict(row[FEATURE_COLS])[0])
            forecasts.append(round(pred, 2))

            # Append predicted row to seed for next iteration
            next_date = seed["date"].max() + pd.Timedelta(days=1)
            new_row = pd.DataFrame({"date": [next_date], "revenue": [pred]})
            seed = pd.concat([seed, new_row], ignore_index=True)

        logger.info(f"Forecasted {len(forecasts)} days of revenue.")
        return forecasts

    def _compute_metrics(self, test_df: pd.DataFrame) -> Dict[str, float]:
        X_test = test_df[FEATURE_COLS]
        y_test = test_df["revenue"].values
        y_pred = self.model.predict(X_test)

        mae  = float(np.mean(np.abs(y_test - y_pred)))
        rmse = float(np.sqrt(np.mean((y_test - y_pred) ** 2)))
        mape = float(np.mean(np.abs((y_test - y_pred) / (y_test + 1e-9)))) * 100

        return {"RMSE": round(rmse, 2), "MAE": round(mae, 2), "MAPE": round(mape, 4)}

    def evaluate(self, df: pd.DataFrame) -> Dict[str, float]:
        df = df.sort_values("date").reset_index(drop=True)
        df = self._featurize(df).dropna(subset=FEATURE_COLS)
        cutoff = df["date"].max() - pd.Timedelta(days=90)
        test_df = df[df["date"] > cutoff]
        return self._compute_metrics(test_df)

    def get_feature_importance(self) -> pd.Series:
        return pd.Series(
            self.model.feature_importances_, index=FEATURE_COLS
        ).sort_values(ascending=False)

    def write_forecast_to_db(self, forecast: List[float], conn: Any) -> None:
        """Write 30-day forecast JSON to the latest health_scores row."""
        forecast_json = json.dumps(forecast)
        cur = conn.cursor()
        cur.execute(
            "UPDATE health_scores SET finance_forecast = ? WHERE score_date = "
            "(SELECT MAX(score_date) FROM health_scores)",
            (forecast_json,),
        )
        conn.commit()
        logger.info(f"Forecast written to health_scores (n={len(forecast)}).")

    def save_model(self) -> None:
        save_model({"model": self.model, "lags": self.lags, "horizon": self.horizon,
                    "last_known_df": self._last_known_df}, MODEL_NAME)

    def load_model(self) -> None:
        artifact = load_model(MODEL_NAME)
        self.model = artifact["model"]
        self.lags = artifact["lags"]
        self.horizon = artifact["horizon"]
        self._last_known_df = artifact["last_known_df"]
        self._fitted = True
