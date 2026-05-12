"""
ml/ai_layer/diagnostic.py
────────────────────────────────────────────────────────────────────────────────
AI Diagnostic Layer — Groq API + LLaMA 3 integration.

Errors are now surfaced explicitly so you know exactly why AI failed.
"""

import json
import logging
import os
from datetime import date as _date, timedelta as _td
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd
from dotenv import load_dotenv

from .prompt_templates import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

# Always load .env when this module is imported (covers dashboard + pipeline)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)


def _read(conn, sql) -> pd.DataFrame:
    try:
        return pd.read_sql(sql, conn)
    except Exception as exc:
        logger.warning(f"Query failed: {exc}")
        return pd.DataFrame()


class DiagnosticReporter:
    def __init__(self, config: Dict):
        self.model       = config["ai"]["model"]
        self.temperature = config["ai"]["temperature"]
        self.max_tokens  = config["ai"]["max_tokens"]
        self._client     = None
        self._last_error = ""   # store last error so dashboard can show it

    # ── Groq client ──────────────────────────────────────────────────────────

    def _get_client(self):
        """
        Initialize Groq client. Raises a clear exception on every failure type
        instead of silently returning None.
        """
        if self._client is not None:
            return self._client

        # Reload .env in case it was added after process start
        if _env_path.exists():
            load_dotenv(_env_path, override=True)

        api_key = os.environ.get("GROQ_API_KEY", "").strip()

        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set.\n"
                f"  1. Open {_env_path}\n"
                "  2. Add: GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx\n"
                "  3. Get a FREE key at https://console.groq.com/keys\n"
                "  4. Re-run: python run_pipeline.py --mode ai"
            )

        if api_key == "your_groq_api_key_here":
            raise EnvironmentError(
                "GROQ_API_KEY is still the placeholder value.\n"
                f"  Open {_env_path} and replace it with your real key.\n"
                "  Get a FREE key at https://console.groq.com/keys"
            )

        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "groq package not installed.\n"
                "  Run: pip install groq"
            )

        self._client = Groq(api_key=api_key)
        return self._client

    # ── Context builder ───────────────────────────────────────────────────────

    def build_context(self, conn: Any) -> Dict:
        d7  = (_date.today() - _td(days=7)).isoformat()
        d30 = (_date.today() - _td(days=30)).isoformat()

        score_df = _read(conn, "SELECT * FROM health_scores ORDER BY score_date DESC LIMIT 1")
        if score_df.empty:
            logger.warning("No health scores in DB — run scoring step first.")
            return {}

        row = score_df.iloc[0]

        anomalies_df = _read(conn,
            f"SELECT domain, description, severity FROM anomaly_log "
            f"WHERE detected_at >= '{d7}' ORDER BY severity DESC LIMIT 10"
        )
        anomalies = anomalies_df.to_dict("records") if not anomalies_df.empty else []

        try:
            hr_df = _read(conn,
                "SELECT AVG(CAST(attrition AS FLOAT)) * 100 AS rate FROM hr_employees"
            )
            attrition_rate = round(float(hr_df["rate"].iloc[0] or 0), 1)
        except Exception:
            attrition_rate = 0.0

        try:
            ops_df = _read(conn,
                f"SELECT AVG(sla_compliance_pct) AS sla, AVG(system_uptime_pct) AS uptime "
                f"FROM ops_daily WHERE date >= '{d30}'"
            )
            ops_sla    = round(float(ops_df["sla"].iloc[0] or 0), 1)
            ops_uptime = round(float(ops_df["uptime"].iloc[0] or 0), 2)
        except Exception:
            ops_sla, ops_uptime = 0.0, 0.0

        try:
            fin_df = _read(conn,
                f"SELECT AVG(revenue) AS avg_rev, AVG(profit_margin) AS avg_margin "
                f"FROM finance_daily WHERE date >= '{d30}'"
            )
            avg_rev    = round(float(fin_df["avg_rev"].iloc[0] or 0), 0)
            avg_margin = round(float(fin_df["avg_margin"].iloc[0] or 0), 1)
        except Exception:
            avg_rev, avg_margin = 0.0, 0.0

        forecast_raw = row.get("finance_forecast", "[]") or "[]"
        try:
            forecast = json.loads(forecast_raw)[:7]
        except (json.JSONDecodeError, TypeError):
            forecast = []

        return {
            "report_date":                str(_date.today()),
            "composite_score":            round(float(row["composite_score"]), 1),
            "score_band":                 str(row["score_band"]),
            "finance_score":              round(float(row["finance_score"]), 1),
            "hr_score":                   round(float(row["hr_score"]), 1),
            "ops_score":                  round(float(row["ops_score"]), 1),
            "delta_vs_prev_day":          round(float(row.get("delta_vs_prev_day") or 0), 1),
            "anomaly_penalty":            round(float(row.get("anomaly_penalty") or 0), 1),
            "active_anomalies":           anomalies,
            "hr_attrition_rate_pct":      attrition_rate,
            "ops_sla_30d_avg":            ops_sla,
            "ops_uptime_30d_avg":         ops_uptime,
            "finance_avg_revenue_30d":    avg_rev,
            "finance_avg_margin_30d_pct": avg_margin,
            "revenue_forecast_7d":        forecast,
        }

    # ── Report generation ─────────────────────────────────────────────────────

    def generate_report(self, context: Dict) -> Tuple[str, bool]:
        """
        Returns (report_text, is_fallback).
        Logs the exact error so it's visible in pipeline output.
        """
        try:
            client = self._get_client()
        except (EnvironmentError, ImportError) as exc:
            self._last_error = str(exc)
            logger.error(f"\n{'='*60}\nGROQ AI UNAVAILABLE\n{exc}\n{'='*60}")
            return self.fallback_report(context), True

        user_prompt = build_user_prompt(context)
        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            text = response.choices[0].message.content.strip()
            logger.info(f"✅ Groq AI report generated ({len(text.split())} words, model={self.model})")
            self._last_error = ""
            return text, False

        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            logger.error(f"\n{'='*60}\nGROQ API CALL FAILED: {exc}\n{'='*60}")
            return self.fallback_report(context), True

    def fallback_report(self, context: Dict) -> str:
        band    = context.get("score_band", "Unknown")
        score   = context.get("composite_score", 0)
        finance = context.get("finance_score", 0)
        hr      = context.get("hr_score", 0)
        ops     = context.get("ops_score", 0)
        anomalies = context.get("active_anomalies", [])

        status_map = {
            "Healthy":  "The business is operating in a healthy state.",
            "At Risk":  "The business is showing signs of stress and requires attention.",
            "Critical": "The business is in a critical state and requires immediate action.",
        }
        status = status_map.get(band, "Business status could not be determined.")
        weakest = min([("Finance", finance), ("HR", hr), ("Operations", ops)], key=lambda x: x[1])

        return f"""## Executive Summary
{status} The composite Business Health Score stands at **{score}/100** (Finance: {finance}, HR: {hr}, Operations: {ops}).

## Risk Factors

### 1. Weakest Domain — {weakest[0]} ({weakest[1]}/100)
{weakest[0]} is the lowest-performing domain and warrants priority investigation. Scores below 75 indicate metrics are outside target ranges and corrective action is required.

### 2. Active Anomalies ({len(anomalies)} detected)
{len(anomalies)} anomaly event(s) were flagged in the last 7 days by the ML detection layer.
{"Most critical: " + anomalies[0].get("description", "See anomaly log for details.") if anomalies else "No anomaly descriptions available."}

### 3. Score Trend
The composite score changed by **{context.get("delta_vs_prev_day", 0):+.1f} points** vs the previous day.
{"This downward trend warrants monitoring." if context.get("delta_vs_prev_day", 0) < 0 else "The trend is stable or improving."}

## Recommended Actions
1. Investigate {weakest[0]} KPIs and identify root causes — Department Head — within 48 hours.
2. Review and resolve all active anomaly events — Operations team — within 24 hours.
3. Schedule a business health review with all department heads — Leadership — within 1 week.

## 30-Day Outlook
{"Stabilization is expected if recommended actions are taken promptly." if band != "Critical" else "Urgent intervention required to prevent further score degradation."}
""".strip()

    # ── Store & retrieve ──────────────────────────────────────────────────────

    def generate_and_store(self, conn: Any) -> str:
        context = self.build_context(conn)
        if not context:
            return ""
        report_text, is_fallback = self.generate_report(context)
        self.write_to_db(report_text, is_fallback, context, conn)
        return report_text

    def write_to_db(self, report_text: str, is_fallback: bool,
                    context: Dict, conn: Any) -> None:
        import sqlite3
        today      = str(_date.today())
        word_count = len(report_text.split())
        model_used = self.model if not is_fallback else "fallback"

        if isinstance(conn, sqlite3.Connection):
            conn.execute(
                "INSERT OR REPLACE INTO ai_reports "
                "(report_date, composite_score, score_band, report_text, "
                " model_used, is_fallback, word_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (today, context.get("composite_score", 0),
                 context.get("score_band", "Unknown"),
                 report_text, model_used, int(is_fallback), word_count),
            )
            conn.commit()
        else:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO ai_reports "
                "(report_date, composite_score, score_band, report_text, "
                " model_used, is_fallback, word_count) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (report_date) DO UPDATE SET report_text=EXCLUDED.report_text",
                (today, context.get("composite_score", 0),
                 context.get("score_band", "Unknown"),
                 report_text, model_used, int(is_fallback), word_count),
            )
            conn.commit()
        logger.info(f"AI report stored ({word_count} words, fallback={is_fallback}).")
