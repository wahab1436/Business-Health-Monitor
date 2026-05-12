"""
data/generators/ops_generator.py
────────────────────────────────────────────────────────────────────────────────
Synthetic operations data generator.

Generates 2 years of daily operational metrics including SLA compliance,
ticket volume, resolution time, and system uptime, with injected outage events.
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Optional


def generate_ops_data(
    n_days: int = 730,
    seed: int = 42,
    sla_target: float = 95.0,
    uptime_target: float = 99.9,
    avg_resolution_mean: float = 4.0,
    ticket_lambda: float = 150.0,
    anomaly_rate: float = 0.03,
    start_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Generate synthetic daily operations data.

    Parameters
    ----------
    n_days : int
        Number of daily records.
    seed : int
        Random seed.
    sla_target : float
        Target SLA compliance percentage (default 95%).
    uptime_target : float
        Target system uptime percentage (default 99.9%).
    avg_resolution_mean : float
        Mean resolution time in hours (log-normal distribution).
    ticket_lambda : float
        Poisson lambda for daily ticket volume.
    anomaly_rate : float
        Fraction of days that have outage/incident events.
    start_date : date, optional
        Defaults to 2 years before today.

    Returns
    -------
    pd.DataFrame with columns:
        date, sla_compliance_pct, ticket_volume, avg_resolution_hours,
        system_uptime_pct, efficiency_score, anomaly_flag
    """
    rng = np.random.default_rng(seed)

    if start_date is None:
        start_date = date.today() - timedelta(days=n_days)

    dates = pd.date_range(start=start_date, periods=n_days, freq="D")
    day_of_week = dates.dayofweek  # 0=Mon, 6=Sun

    # ── Ticket Volume: Poisson with weekly seasonality ─────────────────────────
    # Higher on Mon/Tue, lower on weekends
    weekly_weight = np.where(day_of_week < 5, 1.0, 0.4)
    ticket_volume = rng.poisson(lam=ticket_lambda * weekly_weight)

    # ── Resolution Time: Log-normal ────────────────────────────────────────────
    sigma = 0.5
    mu = np.log(avg_resolution_mean) - 0.5 * sigma ** 2
    avg_resolution_hours = rng.lognormal(mean=mu, sigma=sigma, size=n_days)

    # ── SLA Compliance: Gaussian noise around target ───────────────────────────
    sla_noise = rng.normal(0, 1.5, size=n_days)
    sla_compliance_pct = np.clip(sla_target + sla_noise, 60.0, 100.0)

    # ── System Uptime: near 100% with rare drops ───────────────────────────────
    uptime_noise = rng.normal(0, 0.2, size=n_days)
    system_uptime_pct = np.clip(uptime_target + uptime_noise, 90.0, 100.0)

    # ── Anomaly Injection: System Outage Events ────────────────────────────────
    n_anomalies = max(1, int(n_days * anomaly_rate))
    anomaly_indices = rng.choice(n_days, size=n_anomalies, replace=False)
    anomaly_flag = np.zeros(n_days, dtype=bool)
    anomaly_flag[anomaly_indices] = True

    for idx in anomaly_indices:
        # Outage: correlated drops across multiple metrics
        sla_compliance_pct[idx] = rng.uniform(60.0, 80.0)
        system_uptime_pct[idx] = rng.uniform(85.0, 95.0)
        avg_resolution_hours[idx] = rng.uniform(8.0, 24.0)
        ticket_volume[idx] = int(ticket_volume[idx] * rng.uniform(2.0, 3.5))

    # ── Efficiency Score: weighted composite ───────────────────────────────────
    # Normalize each metric to 0-100 then weight
    sla_norm = sla_compliance_pct  # already 0-100
    uptime_norm = system_uptime_pct  # already 0-100
    resolution_norm = np.clip(100.0 - (avg_resolution_hours - 1.0) * 5.0, 0.0, 100.0)

    efficiency_score = (0.40 * sla_norm + 0.35 * uptime_norm + 0.25 * resolution_norm)
    efficiency_score = np.clip(efficiency_score, 0.0, 100.0)

    df = pd.DataFrame(
        {
            "date": dates.date,
            "sla_compliance_pct": sla_compliance_pct.round(2),
            "ticket_volume": ticket_volume,
            "avg_resolution_hours": avg_resolution_hours.round(2),
            "system_uptime_pct": system_uptime_pct.round(3),
            "efficiency_score": efficiency_score.round(2),
            "anomaly_flag": anomaly_flag,
        }
    )

    return df


if __name__ == "__main__":
    df = generate_ops_data()
    print(df.head(10).to_string())
    print(f"\nShape: {df.shape}")
    print(f"Anomaly count: {df['anomaly_flag'].sum()} ({df['anomaly_flag'].mean()*100:.1f}%)")
    print(f"\nMean SLA: {df['sla_compliance_pct'].mean():.2f}%")
    print(f"Mean Uptime: {df['system_uptime_pct'].mean():.3f}%")
