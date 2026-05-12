"""
data/pipeline/ingest.py
────────────────────────────────────────────────────────────────────────────────
SQL Ingestion Pipeline.

Reads generated CSVs, validates schema, and bulk inserts into the database.
Idempotent: checks existing records before inserting to allow safe re-runs.
All errors are logged to logs/ingestion.log.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from .db_connection import get_connection

logger = logging.getLogger(__name__)

# ─── Expected schemas ─────────────────────────────────────────────────────────

FINANCE_COLS = {"date", "revenue", "expenses", "profit_margin", "cash_flow", "anomaly_flag"}
HR_EMPLOYEE_COLS = {"employee_id", "department", "tenure_months", "salary",
                    "satisfaction_score", "attrition", "absenteeism_days", "anomaly_flag"}
HR_SNAPSHOT_COLS = {"employee_id", "snapshot_date", "department", "satisfaction_score",
                    "absenteeism_days", "attrition_flag", "anomaly_flag"}
OPS_COLS = {"date", "sla_compliance_pct", "ticket_volume", "avg_resolution_hours",
            "system_uptime_pct", "efficiency_score", "anomaly_flag"}


def validate_schema(df: pd.DataFrame, expected_cols: set, name: str) -> bool:
    """Raise ValueError if required columns are missing."""
    missing = expected_cols - set(df.columns)
    if missing:
        raise ValueError(f"[{name}] Missing columns: {missing}")
    logger.info(f"[{name}] Schema valid — {len(df)} rows")
    return True


def _execute_many(conn: Any, sql: str, rows: list) -> int:
    """Execute a batch insert. Returns number of rows inserted."""
    cur = conn.cursor()
    cur.executemany(sql, rows)
    conn.commit()
    return cur.rowcount


def ingest_finance(csv_path: Path) -> int:
    """
    Load finance CSV → validate → bulk insert into finance_daily.
    Skips dates already present in the database (idempotent).
    """
    logger.info(f"Ingesting finance data from {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["date"])
    validate_schema(df, FINANCE_COLS, "finance")

    conn = get_connection()
    try:
        # Fetch existing dates
        existing = pd.read_sql("SELECT date FROM finance_daily", conn)
        existing_dates = set(existing["date"].astype(str).tolist()) if not existing.empty else set()

        df["date_str"] = df["date"].astype(str)
        new_rows = df[~df["date_str"].isin(existing_dates)].drop(columns=["date_str"])
        logger.info(f"Finance: {len(new_rows)} new rows to insert (skipped {len(df) - len(new_rows)})")

        if len(new_rows) == 0:
            return 0

        sql = """
            INSERT INTO finance_daily
                (date, revenue, expenses, profit_margin, cash_flow, anomaly_flag)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                str(r["date"])[:10],
                float(r["revenue"]),
                float(r["expenses"]),
                float(r["profit_margin"]),
                float(r["cash_flow"]),
                int(bool(r["anomaly_flag"])),
            )
            for _, r in new_rows.iterrows()
        ]
        n = _execute_many(conn, sql, rows)
        logger.info(f"Finance: inserted {n} rows")
        return n
    except Exception as exc:
        logger.error(f"Finance ingestion failed: {exc}")
        raise
    finally:
        conn.close()


def ingest_hr(employees_path: Path, snapshots_path: Path) -> int:
    """
    Load HR CSVs → validate → bulk insert into hr_employees and hr_monthly_snapshot.
    """
    logger.info(f"Ingesting HR employees from {employees_path}")
    emp_df = pd.read_csv(employees_path)
    validate_schema(emp_df, HR_EMPLOYEE_COLS, "hr_employees")

    logger.info(f"Ingesting HR snapshots from {snapshots_path}")
    snap_df = pd.read_csv(snapshots_path, parse_dates=["snapshot_date"])
    validate_schema(snap_df, HR_SNAPSHOT_COLS, "hr_monthly_snapshot")

    conn = get_connection()
    try:
        # Employees: upsert by employee_id
        existing_emp = pd.read_sql("SELECT employee_id FROM hr_employees", conn)
        existing_ids = set(existing_emp["employee_id"].tolist()) if not existing_emp.empty else set()
        new_emp = emp_df[~emp_df["employee_id"].isin(existing_ids)]
        logger.info(f"HR employees: {len(new_emp)} new records")

        if len(new_emp) > 0:
            emp_sql = """
                INSERT INTO hr_employees
                    (employee_id, department, tenure_months, salary,
                     satisfaction_score, attrition, absenteeism_days,
                     anomaly_flag, attrition_probability)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            emp_rows = [
                (
                    int(r["employee_id"]),
                    str(r["department"]),
                    int(r["tenure_months"]),
                    float(r["salary"]),
                    float(r["satisfaction_score"]),
                    int(bool(r["attrition"])),
                    int(r["absenteeism_days"]),
                    int(bool(r["anomaly_flag"])),
                    float(r.get("attrition_probability", 0.0)),
                )
                for _, r in new_emp.iterrows()
            ]
            _execute_many(conn, emp_sql, emp_rows)

        # Snapshots: insert new (employee_id, snapshot_date) pairs
        existing_snaps = pd.read_sql(
            "SELECT employee_id, snapshot_date FROM hr_monthly_snapshot", conn
        )
        if not existing_snaps.empty:
            existing_keys = set(
                zip(
                    existing_snaps["employee_id"].tolist(),
                    existing_snaps["snapshot_date"].astype(str).tolist(),
                )
            )
        else:
            existing_keys = set()

        snap_df["_key"] = list(
            zip(snap_df["employee_id"], snap_df["snapshot_date"].astype(str))
        )
        new_snaps = snap_df[~snap_df["_key"].isin(existing_keys)].drop(columns=["_key"])
        logger.info(f"HR snapshots: {len(new_snaps)} new records")

        if len(new_snaps) > 0:
            snap_sql = """
                INSERT INTO hr_monthly_snapshot
                    (employee_id, snapshot_date, department, satisfaction_score,
                     absenteeism_days, attrition_flag, anomaly_flag)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            snap_rows = [
                (
                    int(r["employee_id"]),
                    str(r["snapshot_date"])[:10],
                    str(r["department"]),
                    float(r["satisfaction_score"]),
                    int(r["absenteeism_days"]),
                    int(bool(r["attrition_flag"])),
                    int(bool(r["anomaly_flag"])),
                )
                for _, r in new_snaps.iterrows()
            ]
            _execute_many(conn, snap_sql, snap_rows)

        return len(new_emp) + len(new_snaps)
    except Exception as exc:
        logger.error(f"HR ingestion failed: {exc}")
        raise
    finally:
        conn.close()


def ingest_ops(csv_path: Path) -> int:
    """
    Load ops CSV → validate → bulk insert into ops_daily.
    """
    logger.info(f"Ingesting operations data from {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["date"])
    validate_schema(df, OPS_COLS, "ops")

    conn = get_connection()
    try:
        existing = pd.read_sql("SELECT date FROM ops_daily", conn)
        existing_dates = set(existing["date"].astype(str).tolist()) if not existing.empty else set()

        df["date_str"] = df["date"].astype(str)
        new_rows = df[~df["date_str"].isin(existing_dates)].drop(columns=["date_str"])
        logger.info(f"Ops: {len(new_rows)} new rows to insert")

        if len(new_rows) == 0:
            return 0

        sql = """
            INSERT INTO ops_daily
                (date, sla_compliance_pct, ticket_volume, avg_resolution_hours,
                 system_uptime_pct, efficiency_score, anomaly_flag)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                str(r["date"])[:10],
                float(r["sla_compliance_pct"]),
                int(r["ticket_volume"]),
                float(r["avg_resolution_hours"]),
                float(r["system_uptime_pct"]),
                float(r["efficiency_score"]),
                int(bool(r["anomaly_flag"])),
            )
            for _, r in new_rows.iterrows()
        ]
        n = _execute_many(conn, sql, rows)
        logger.info(f"Ops: inserted {n} rows")
        return n
    except Exception as exc:
        logger.error(f"Ops ingestion failed: {exc}")
        raise
    finally:
        conn.close()
