"""
ml/utils/preprocessing.py
────────────────────────────────────────────────────────────────────────────────
Shared preprocessing utilities used across all ML models.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from typing import List, Optional, Tuple


def normalize(
    df: pd.DataFrame,
    cols: List[str],
    scaler: Optional[StandardScaler] = None,
    fit: bool = True,
) -> Tuple[pd.DataFrame, StandardScaler]:
    """
    StandardScale specified columns in-place.

    Parameters
    ----------
    df : pd.DataFrame
    cols : list of column names to scale
    scaler : existing StandardScaler (pass for predict-time use)
    fit : if True, fit the scaler on df; otherwise transform only

    Returns
    -------
    (scaled_df, scaler)
    """
    if scaler is None:
        scaler = StandardScaler()

    df = df.copy()
    if fit:
        df[cols] = scaler.fit_transform(df[cols].astype(float))
    else:
        df[cols] = scaler.transform(df[cols].astype(float))

    return df, scaler


def encode_categoricals(
    df: pd.DataFrame,
    cols: List[str],
    encoders: Optional[dict] = None,
    fit: bool = True,
) -> Tuple[pd.DataFrame, dict]:
    """
    Label-encode categorical columns.

    Returns
    -------
    (encoded_df, {col: LabelEncoder})
    """
    df = df.copy()
    if encoders is None:
        encoders = {}

    for col in cols:
        if col not in df.columns:
            continue
        if fit:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
        else:
            le = encoders[col]
            # Handle unseen labels gracefully
            known = set(le.classes_)
            df[col] = df[col].astype(str).apply(
                lambda x: x if x in known else le.classes_[0]
            )
            df[col] = le.transform(df[col])

    return df, encoders


def create_lag_features(
    df: pd.DataFrame,
    target_col: str,
    lags: List[int],
    date_col: str = "date",
) -> pd.DataFrame:
    """
    Create lag and rolling statistics features for time-series ML.

    Parameters
    ----------
    df : DataFrame sorted by date
    target_col : column to lag
    lags : list of lag day counts e.g. [7, 14, 30]
    date_col : date column name

    Returns
    -------
    DataFrame with lag_{n} and rolling_mean/std_30 columns added.
    """
    df = df.sort_values(date_col).copy()

    for lag in lags:
        df[f"lag_{lag}"] = df[target_col].shift(lag)

    df["rolling_mean_30"] = df[target_col].shift(1).rolling(30).mean()
    df["rolling_std_30"]  = df[target_col].shift(1).rolling(30).std()

    # Date features
    df[date_col] = pd.to_datetime(df[date_col])
    df["day_of_week"] = df[date_col].dt.dayofweek
    df["month"]       = df[date_col].dt.month
    df["quarter"]     = df[date_col].dt.quarter

    return df


def handle_missing(df: pd.DataFrame, strategy: str = "median") -> pd.DataFrame:
    """
    Fill missing values in numeric columns.

    Parameters
    ----------
    strategy : 'median' | 'mean' | 'zero'
    """
    df = df.copy()
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in num_cols:
        if df[col].isna().any():
            if strategy == "median":
                df[col].fillna(df[col].median(), inplace=True)
            elif strategy == "mean":
                df[col].fillna(df[col].mean(), inplace=True)
            else:
                df[col].fillna(0, inplace=True)

    return df
