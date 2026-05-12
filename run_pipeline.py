"""
run_pipeline.py
────────────────────────────────────────────────────────────────────────────────
Business Health Monitor — Master Pipeline Orchestrator

Usage:
    python run_pipeline.py --mode full       # Init DB → Generate → Ingest → ML → Score → AI
    python run_pipeline.py --mode generate   # Data generation only
    python run_pipeline.py --mode ingest     # SQL ingestion only
    python run_pipeline.py --mode ml         # ML models only (data must exist)
    python run_pipeline.py --mode score      # Scoring engine only
    python run_pipeline.py --mode ai         # AI diagnostic report only
    python run_pipeline.py --mode init-db    # Initialize database schema only
"""

import argparse
import logging
import os
import sqlite3 as _sqlite3
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ─── Resolve project root (works regardless of where you run from) ─────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)           # make all relative paths work from here
sys.path.insert(0, str(PROJECT_ROOT))

# ─── Load environment & config ────────────────────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env")

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

# ─── Logging setup ────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=getattr(logging, CONFIG["pipeline"]["log_level"], "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["pipeline"]["log_file"]),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("run_pipeline")


# ─── Step functions ───────────────────────────────────────────────────────────

def step_init_db():
    """Initialize database schema from sql/schema.sql."""
    logger.info("=== STEP: Initialize Database ===")
    from data.pipeline.db_connection import get_connection

    schema_path = PROJECT_ROOT / "sql" / "schema.sql"
    with open(schema_path) as f:
        schema_sql = f.read()

    conn = get_connection()
    try:
        if isinstance(conn, _sqlite3.Connection):
            # executescript handles multiple statements and auto-commits
            conn.executescript(schema_sql)
            logger.info("SQLite schema initialized successfully.")
        else:
            # PostgreSQL
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()
            logger.info("PostgreSQL schema initialized successfully.")
    except Exception as exc:
        logger.error(f"Schema init failed: {exc}")
        raise
    finally:
        conn.close()


def step_generate():
    """Run all three synthetic data generators."""
    logger.info("=== STEP: Data Generation ===")
    from data.generators.finance_generator import generate_finance_data
    from data.generators.hr_generator import generate_employees, generate_monthly_snapshots
    from data.generators.ops_generator import generate_ops_data

    raw_dir = PROJECT_ROOT / "data" / "raw"
    raw_dir.mkdir(exist_ok=True)

    cfg   = CONFIG["data_generation"]
    seed  = cfg["seed"]
    n_days = cfg["n_days"]
    n_emp  = cfg["n_employees"]

    t0 = time.perf_counter()

    finance_df = generate_finance_data(n_days=n_days, seed=seed)
    finance_df.to_csv(raw_dir / "finance.csv", index=False)
    logger.info(f"Finance data generated: {len(finance_df)} rows")

    employees_df = generate_employees(n=n_emp, seed=seed)
    employees_df.to_csv(raw_dir / "hr_employees.csv", index=False)
    logger.info(f"HR employees generated: {len(employees_df)} rows")

    snapshots_df = generate_monthly_snapshots(employees_df=employees_df, n_months=24, seed=seed)
    snapshots_df.to_csv(raw_dir / "hr_monthly_snapshots.csv", index=False)
    logger.info(f"HR monthly snapshots generated: {len(snapshots_df)} rows")

    ops_df = generate_ops_data(n_days=n_days, seed=seed)
    ops_df.to_csv(raw_dir / "ops.csv", index=False)
    logger.info(f"Operations data generated: {len(ops_df)} rows")

    logger.info(f"Data generation complete in {time.perf_counter() - t0:.2f}s")


def step_ingest():
    """Ingest generated CSVs into the SQL database."""
    logger.info("=== STEP: SQL Ingestion ===")
    from data.pipeline.ingest import ingest_finance, ingest_hr, ingest_ops

    raw_dir = PROJECT_ROOT / "data" / "raw"
    t0 = time.perf_counter()
    ingest_finance(raw_dir / "finance.csv")
    ingest_hr(
        employees_path=raw_dir / "hr_employees.csv",
        snapshots_path=raw_dir / "hr_monthly_snapshots.csv",
    )
    ingest_ops(raw_dir / "ops.csv")
    logger.info(f"SQL ingestion complete in {time.perf_counter() - t0:.2f}s")


def step_ml():
    """Train and run all five ML models."""
    logger.info("=== STEP: ML Models ===")
    from data.pipeline.db_connection import get_connection
    from ml.models.finance_anomaly import FinanceAnomalyDetector
    from ml.models.revenue_forecast import RevenueForecaster
    from ml.models.hr_attrition import AttritionClassifier
    from ml.models.hr_anomaly import HRAnomalyDetector
    from ml.models.ops_anomaly import OpsAnomalyDetector
    import pandas as pd

    conn = get_connection()

    # ── Model 1: Finance Anomaly ───────────────────────────────────────────────
    logger.info("Training Finance Anomaly Detector…")
    finance_df = pd.read_sql("SELECT * FROM finance_daily ORDER BY date", conn)
    if finance_df.empty:
        logger.error("finance_daily table is empty — did ingest run?")
    else:
        fad = FinanceAnomalyDetector(CONFIG)
        fad.train(finance_df)
        anomalies = fad.predict(finance_df)
        fad.write_anomalies_to_db(anomalies, conn)
        fad.save_model()
        logger.info(f"Finance anomalies detected: {anomalies['is_anomaly'].sum()}")

    # ── Model 2: Revenue Forecaster ───────────────────────────────────────────
    logger.info("Training Revenue Forecaster…")
    finance_df = pd.read_sql("SELECT * FROM finance_daily ORDER BY date", conn)
    if not finance_df.empty:
        rf = RevenueForecaster(CONFIG)
        rf.train(finance_df)
        forecast = rf.forecast(n_days=30)
        rf.write_forecast_to_db(forecast, conn)
        rf.save_model()
        logger.info("Revenue forecast for next 30 days written to DB.")

    # ── Model 3: HR Attrition Classifier ─────────────────────────────────────
    logger.info("Training HR Attrition Classifier…")
    emp_df  = pd.read_sql("SELECT * FROM hr_employees", conn)
    snap_df = pd.read_sql("SELECT * FROM hr_monthly_snapshot", conn)
    if not emp_df.empty:
        ac = AttritionClassifier(CONFIG)
        ac.train(emp_df, snap_df)
        emp_df = ac.predict_risk(emp_df)
        ac.write_risk_scores_to_db(emp_df, conn)
        ac.save_model()
        threshold = CONFIG["ml"]["hr_attrition"]["risk_threshold"]
        high_risk = (emp_df["attrition_probability"] > threshold).sum()
        logger.info(f"High-risk employees identified: {high_risk}")

    # ── Model 4: HR Anomaly Detector ─────────────────────────────────────────
    logger.info("Training HR Anomaly Detector…")
    snap_df = pd.read_sql("SELECT * FROM hr_monthly_snapshot", conn)
    if not snap_df.empty:
        # Build aggregated features — column names must match HRAnomalyDetector.FEATURE_COLS
        hr_agg = snap_df.groupby("department").agg(
            monthly_attrition_rate=("attrition_flag", "mean"),
            avg_satisfaction=("satisfaction_score", "mean"),
            avg_absenteeism_rate=("absenteeism_days", "mean"),
        ).reset_index()
        had = HRAnomalyDetector(CONFIG)
        had.train(hr_agg)
        hr_anomalies = had.predict(hr_agg)
        had.write_anomalies_to_db(hr_anomalies, conn)
        had.save_model()
        logger.info(f"HR anomalies detected: {hr_anomalies['is_anomaly'].sum()}")

    # ── Model 5: Ops Anomaly Detector ────────────────────────────────────────
    logger.info("Training Ops Anomaly Detector…")
    ops_df = pd.read_sql("SELECT * FROM ops_daily ORDER BY date", conn)
    if not ops_df.empty:
        oad = OpsAnomalyDetector(CONFIG)
        oad.train(ops_df)
        ops_anomalies = oad.predict(ops_df)
        oad.write_anomalies_to_db(ops_anomalies, conn)
        oad.save_model()
        logger.info(f"Ops anomalies detected: {ops_anomalies['is_anomaly'].sum()}")

    conn.close()
    logger.info("All ML models complete.")


def step_score():
    """Run the composite scoring engine."""
    logger.info("=== STEP: Health Scoring Engine ===")
    from data.pipeline.db_connection import get_connection
    from ml.scoring.health_scorer import HealthScorer

    conn = get_connection()
    scorer = HealthScorer(CONFIG)
    result = scorer.run(conn)
    conn.close()
    logger.info(
        f"Health Score: {result['composite']:.1f} ({result['band']}) | "
        f"Finance={result['finance']:.1f}  HR={result['hr']:.1f}  Ops={result['ops']:.1f}"
    )


def step_ai():
    """Generate AI diagnostic report via Groq API."""
    logger.info("=== STEP: AI Diagnostic Report ===")
    from data.pipeline.db_connection import get_connection
    from ml.ai_layer.diagnostic import DiagnosticReporter

    conn = get_connection()
    reporter = DiagnosticReporter(CONFIG)
    report = reporter.generate_and_store(conn)
    conn.close()
    logger.info(f"AI report generated ({len(report.split())} words).")


# ─── Main ─────────────────────────────────────────────────────────────────────

STEPS = {
    "generate": step_generate,
    "ingest":   step_ingest,
    "ml":       step_ml,
    "score":    step_score,
    "ai":       step_ai,
    "init-db":  step_init_db,
}

# init-db is ALWAYS first so tables exist before any other step
FULL_ORDER = ["init-db", "generate", "ingest", "ml", "score", "ai"]


def _print_startup_banner():
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    print()
    print("=" * 62)
    print("  Business Health Monitor")
    print("=" * 62)
    if not api_key or api_key == "your_groq_api_key_here":
        print("  ⚠️  AI reports DISABLED — GROQ_API_KEY not set")
        print()
        print("  To enable AI reports:")
        print(f"  1. Open  {PROJECT_ROOT / '.env'}")
        print("  2. Replace  your_groq_api_key_here  with your key")
        print("  3. Free key: https://console.groq.com/keys")
        print()
        print("  All other pipeline steps will run normally.")
    else:
        print(f"  ✅ GROQ_API_KEY loaded ({api_key[:8]}...{api_key[-4:]})")
        print("  ✅ AI diagnostic reports enabled")
    print("=" * 62)
    print()


def main():
    parser = argparse.ArgumentParser(description="Business Health Monitor Pipeline")
    parser.add_argument(
        "--mode",
        choices=list(STEPS.keys()) + ["full"],
        default="full",
        help="Which pipeline stage to run.",
    )
    args = parser.parse_args()

    _print_startup_banner()
    logger.info(f"Pipeline started — mode={args.mode}")
    total_start = time.perf_counter()

    if args.mode == "full":
        for step_name in FULL_ORDER:
            logger.info(f"─── Running step: {step_name} ───")
            STEPS[step_name]()
    else:
        STEPS[args.mode]()

    elapsed = time.perf_counter() - total_start
    logger.info(f"✅ Pipeline finished in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
