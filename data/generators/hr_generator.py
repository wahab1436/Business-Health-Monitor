"""
data/generators/hr_generator.py
────────────────────────────────────────────────────────────────────────────────
Synthetic HR data generator.

Generates employee records and monthly KPI snapshots. Attrition is driven by
a logistic function of satisfaction and tenure. Anomalies are injected as
sudden department-level attrition spikes.
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Optional


DEPARTMENTS = ["Engineering", "Sales", "HR", "Finance", "Operations"]

# Department salary base (monthly USD)
DEPT_SALARY_BASE = {
    "Engineering": 8_000,
    "Sales": 6_000,
    "HR": 5_000,
    "Finance": 6_500,
    "Operations": 5_500,
}


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate_employees(
    n: int = 500,
    seed: int = 42,
    anomaly_rate: float = 0.03,
) -> pd.DataFrame:
    """
    Generate a static employee table.

    Parameters
    ----------
    n : int
        Number of employees.
    seed : int
        Random seed.
    anomaly_rate : float
        Fraction of employees flagged as anomaly seeds.

    Returns
    -------
    pd.DataFrame with columns:
        employee_id, department, tenure_months, salary, satisfaction_score,
        attrition, absenteeism_days, anomaly_flag, attrition_probability
    """
    rng = np.random.default_rng(seed)

    employee_ids = np.arange(1, n + 1)
    departments = rng.choice(DEPARTMENTS, size=n)
    tenure_months = rng.integers(1, 121, size=n)  # 1–120 months

    # Salary: department base + tenure multiplier + noise
    salary_base = np.array([DEPT_SALARY_BASE[d] for d in departments], dtype=float)
    tenure_multiplier = 1.0 + (tenure_months / 120) * 0.50  # up to +50% for max tenure
    salary_noise = rng.normal(1.0, 0.08, size=n)
    salary = (salary_base * tenure_multiplier * salary_noise).round(2)

    # Satisfaction score: correlated with tenure (longer tenure = slightly higher)
    # and salary percentile (higher pay = higher satisfaction)
    salary_pct = (salary - salary.min()) / (salary.max() - salary.min())
    tenure_pct = tenure_months / 120.0
    satisfaction_base = 2.5 + 1.5 * (0.5 * salary_pct + 0.5 * tenure_pct)
    satisfaction_noise = rng.normal(0.0, 0.5, size=n)
    satisfaction_score = np.clip(satisfaction_base + satisfaction_noise, 1.0, 5.0).round(2)

    # Attrition: logistic function of low satisfaction and low tenure
    attrition_logit = -2.5 + (-1.8 * (satisfaction_score - 2.5)) + (-0.8 * tenure_pct)
    attrition_prob = _sigmoid(attrition_logit)
    attrition = rng.random(size=n) < attrition_prob

    # Absenteeism: Poisson, higher when satisfaction is low
    absenteeism_lambda = np.clip(6.0 - satisfaction_score, 0.5, 8.0)
    absenteeism_days = rng.poisson(lam=absenteeism_lambda)

    # Anomaly flag
    n_anomalies = max(1, int(n * anomaly_rate))
    anomaly_idx = rng.choice(n, size=n_anomalies, replace=False)
    anomaly_flag = np.zeros(n, dtype=bool)
    anomaly_flag[anomaly_idx] = True
    # Force anomaly employees to have very high attrition probability
    attrition_prob[anomaly_idx] = rng.uniform(0.80, 0.99, size=n_anomalies)
    attrition[anomaly_idx] = True

    df = pd.DataFrame(
        {
            "employee_id": employee_ids,
            "department": departments,
            "tenure_months": tenure_months,
            "salary": salary,
            "satisfaction_score": satisfaction_score,
            "attrition": attrition,
            "absenteeism_days": absenteeism_days,
            "anomaly_flag": anomaly_flag,
            "attrition_probability": attrition_prob.round(4),
        }
    )

    return df


def generate_monthly_snapshots(
    employees_df: pd.DataFrame,
    n_months: int = 24,
    seed: int = 42,
    start_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Generate monthly per-employee KPI snapshots.

    Parameters
    ----------
    employees_df : pd.DataFrame
        Output of generate_employees().
    n_months : int
        Number of months to simulate.
    seed : int
        Random seed.
    start_date : date, optional
        Defaults to n_months before today.

    Returns
    -------
    pd.DataFrame with columns:
        employee_id, snapshot_date, department, satisfaction_score,
        absenteeism_days, attrition_flag, anomaly_flag
    """
    rng = np.random.default_rng(seed + 1)

    if start_date is None:
        today = date.today()
        start_date = date(today.year, today.month, 1) - timedelta(days=n_months * 30)

    records = []
    n_employees = len(employees_df)

    for month_offset in range(n_months):
        snapshot_date = date(
            (start_date.year + (start_date.month - 1 + month_offset) // 12),
            ((start_date.month - 1 + month_offset) % 12) + 1,
            1,
        )

        # Monthly satisfaction drifts slightly
        satisfaction_drift = rng.normal(0.0, 0.1, size=n_employees)
        monthly_satisfaction = np.clip(
            employees_df["satisfaction_score"].values + satisfaction_drift, 1.0, 5.0
        )

        # Monthly absenteeism
        absenteeism_lambda = np.clip(6.0 - monthly_satisfaction, 0.5, 8.0)
        monthly_absenteeism = rng.poisson(lam=absenteeism_lambda)

        # Monthly attrition flag (some employees leave each month)
        monthly_attrition_prob = employees_df["attrition_probability"].values * 0.10
        monthly_attrition = rng.random(size=n_employees) < monthly_attrition_prob

        # Inject department-level anomaly every ~8 months
        anomaly_flag_month = np.zeros(n_employees, dtype=bool)
        if month_offset % 8 == 7:
            anomaly_dept = rng.choice(["Engineering", "Sales", "Operations"])
            dept_mask = employees_df["department"].values == anomaly_dept
            monthly_attrition[dept_mask] = rng.random(dept_mask.sum()) < 0.35
            anomaly_flag_month[dept_mask] = True

        for i, row in employees_df.iterrows():
            records.append(
                {
                    "employee_id": row["employee_id"],
                    "snapshot_date": snapshot_date,
                    "department": row["department"],
                    "satisfaction_score": round(float(monthly_satisfaction[i]), 2),
                    "absenteeism_days": int(monthly_absenteeism[i]),
                    "attrition_flag": bool(monthly_attrition[i]),
                    "anomaly_flag": bool(anomaly_flag_month[i]),
                }
            )

    return pd.DataFrame(records)


if __name__ == "__main__":
    emp = generate_employees()
    print("Employees sample:")
    print(emp.head(5).to_string())
    print(f"\nAttrition rate: {emp['attrition'].mean()*100:.1f}%")

    snaps = generate_monthly_snapshots(emp)
    print(f"\nMonthly snapshots shape: {snaps.shape}")
    print(snaps.head(3).to_string())
