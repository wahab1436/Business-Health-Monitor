"""
data/generators/finance_generator.py
────────────────────────────────────────────────────────────────────────────────
Synthetic finance data generator.

Generates 2 years of daily financial metrics with configurable seasonality,
noise, and injected anomalies. No external dataset dependency.
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Optional


def generate_finance_data(
    n_days: int = 730,
    seed: int = 42,
    base_revenue: float = 100_000.0,
    seasonality_amplitude: float = 0.15,
    noise_std: float = 0.05,
    expense_ratio_min: float = 0.70,
    expense_ratio_max: float = 0.85,
    anomaly_rate: float = 0.03,
    start_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Generate synthetic daily financial data.

    Parameters
    ----------
    n_days : int
        Number of daily records to generate (default: 730 = 2 years).
    seed : int
        Random seed for reproducibility.
    base_revenue : float
        Daily base revenue in USD.
    seasonality_amplitude : float
        Amplitude of the annual seasonal sine wave (fraction of base_revenue).
    noise_std : float
        Standard deviation of Gaussian revenue noise.
    expense_ratio_min / max : float
        Range for the expense-to-revenue ratio.
    anomaly_rate : float
        Fraction of records that are anomalous (revenue drop or expense spike).
    start_date : date, optional
        Start date; defaults to 2 years before today.

    Returns
    -------
    pd.DataFrame with columns:
        date, revenue, expenses, profit_margin, cash_flow, anomaly_flag
    """
    rng = np.random.default_rng(seed)

    if start_date is None:
        start_date = date.today() - timedelta(days=n_days)

    dates = pd.date_range(start=start_date, periods=n_days, freq="D")

    # ── Revenue: base trend + seasonality + noise ──────────────────────────────
    day_index = np.arange(n_days)
    # Slight upward growth trend (2% per year)
    growth = 1.0 + (day_index / 365) * 0.02
    # Annual seasonality via sine wave (peak in Dec, trough in Jun)
    seasonality = 1.0 + seasonality_amplitude * np.sin(
        2 * np.pi * day_index / 365 - np.pi / 2
    )
    # Gaussian noise
    noise = rng.normal(loc=1.0, scale=noise_std, size=n_days)

    revenue = base_revenue * growth * seasonality * noise

    # ── Anomaly injection ──────────────────────────────────────────────────────
    n_anomalies = max(1, int(n_days * anomaly_rate))
    anomaly_indices = rng.choice(n_days, size=n_anomalies, replace=False)
    anomaly_flag = np.zeros(n_days, dtype=bool)
    anomaly_flag[anomaly_indices] = True

    # Apply anomaly: random drop (20-50%) or spike (covered via expenses below)
    for idx in anomaly_indices:
        if rng.random() < 0.6:
            # Revenue drop
            revenue[idx] *= rng.uniform(0.50, 0.80)

    # ── Expenses ───────────────────────────────────────────────────────────────
    expense_ratios = rng.uniform(expense_ratio_min, expense_ratio_max, size=n_days)
    # Expense spike anomalies
    for idx in anomaly_indices:
        if not (revenue[idx] < base_revenue * 0.8):  # expense spike on non-revenue-drop anomalies
            expense_ratios[idx] = rng.uniform(0.90, 1.05)

    expenses = revenue * expense_ratios

    # ── Derived metrics ────────────────────────────────────────────────────────
    profit_margin = (revenue - expenses) / revenue * 100.0

    # Cash flow: rolling 30-day cumulative sum of (revenue - expenses) with shocks
    daily_net = revenue - expenses
    cash_flow = np.cumsum(daily_net)
    # Add random shocks
    shock_indices = rng.choice(n_days, size=max(1, n_days // 60), replace=False)
    for idx in shock_indices:
        cash_flow[idx:] += rng.uniform(-50_000, 30_000)

    df = pd.DataFrame(
        {
            "date": dates.date,
            "revenue": revenue.round(2),
            "expenses": expenses.round(2),
            "profit_margin": profit_margin.round(4),
            "cash_flow": cash_flow.round(2),
            "anomaly_flag": anomaly_flag,
        }
    )

    return df


if __name__ == "__main__":
    df = generate_finance_data()
    print(df.head(10).to_string())
    print(f"\nShape: {df.shape}")
    print(f"Anomaly count: {df['anomaly_flag'].sum()} ({df['anomaly_flag'].mean()*100:.1f}%)")
