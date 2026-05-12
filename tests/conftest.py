"""
tests/conftest.py
────────────────────────────────────────────────────────────────────────────────
Pytest fixtures:
  - in-memory SQLite test database (pre-populated with schema + seed data)
  - small synthetic DataFrames for each domain
  - mock Groq API response
"""

import sqlite3
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pandas as pd
import pytest

# ─── DB fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def schema_sql() -> str:
    return (Path(__file__).parent.parent / "sql" / "schema.sql").read_text()


@pytest.fixture
def test_db(schema_sql) -> Generator[sqlite3.Connection, None, None]:
    """In-memory SQLite DB pre-loaded with schema. Fresh for each test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.executescript(schema_sql)
    conn.commit()
    yield conn
    conn.close()


# ─── Small synthetic DataFrames ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def finance_df_small() -> pd.DataFrame:
    from data.generators.finance_generator import generate_finance_data
    return generate_finance_data(n_days=60, seed=0)


@pytest.fixture(scope="session")
def employees_df_small() -> pd.DataFrame:
    from data.generators.hr_generator import generate_employees
    return generate_employees(n=50, seed=0)


@pytest.fixture(scope="session")
def snapshots_df_small(employees_df_small) -> pd.DataFrame:
    from data.generators.hr_generator import generate_monthly_snapshots
    return generate_monthly_snapshots(employees_df_small, n_months=6, seed=0)


@pytest.fixture(scope="session")
def ops_df_small() -> pd.DataFrame:
    from data.generators.ops_generator import generate_ops_data
    return generate_ops_data(n_days=60, seed=0)


# ─── Config fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def config() -> dict:
    import yaml
    return yaml.safe_load(
        (Path(__file__).parent.parent / "config.yaml").read_text()
    )


# ─── Mock Groq API ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_groq_response() -> MagicMock:
    """Minimal mock of a Groq API chat completion response."""
    mock_msg = MagicMock()
    mock_msg.content = (
        "## Executive Summary\n"
        "The business is operating at moderate health (score: 72/100). "
        "HR attrition is the primary concern.\n\n"
        "## Risk Factors\n"
        "### 1. Elevated Attrition\nAttrition at 18% vs 15% target.\n"
        "### 2. SLA Below Target\nSLA at 93.2%, below 95% target.\n"
        "### 3. Revenue Trend\nRevenue declined 4% in last 7 days.\n\n"
        "## Recommended Actions\n"
        "1. HR review — immediate.\n2. Ops capacity check — 48h.\n3. Finance audit — 1 week.\n\n"
        "## 30-Day Outlook\nStabilization expected with corrective actions."
    )
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp
