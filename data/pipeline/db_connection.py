"""
data/pipeline/db_connection.py
────────────────────────────────────────────────────────────────────────────────
Database connection manager.

Reads DB_URL from .env for PostgreSQL. Falls back to SQLite if DB_URL is not
set. Returns a connection object usable as a context manager.
"""

import os
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Union

import yaml
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Load config for SQLite fallback path
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"
with open(_CONFIG_PATH) as _f:
    _CONFIG = yaml.safe_load(_f)

_SQLITE_PATH = _CONFIG_PATH.parent / _CONFIG["database"]["sqlite_path"]
_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    """
    Return a database connection.

    Uses PostgreSQL if DB_URL env var is set; falls back to SQLite for demo.
    The returned connection has the same interface for both backends
    (psycopg2 or sqlite3).
    """
    db_url = os.environ.get("DB_URL", "").strip()

    if db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url)
            logger.debug("Connected to PostgreSQL.")
            return conn
        except Exception as exc:
            logger.warning(f"PostgreSQL connection failed ({exc}); falling back to SQLite.")

    # SQLite fallback
    conn = sqlite3.connect(str(_SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent read performance
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    logger.debug(f"Connected to SQLite at {_SQLITE_PATH}")
    return conn


@contextmanager
def managed_connection():
    """Context manager that auto-commits and closes the connection."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
