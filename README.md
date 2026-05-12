# 📊 Business Health Monitor

> **An AI-Powered, End-to-End Real-Time Business Intelligence System**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36-red.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🏗️ Architecture

```
Synthetic Data Generator
        │
        ▼
SQL Database (SQLite / PostgreSQL)
        │
        ▼
ML Engine
 ├─ Finance Anomaly Detector  (Isolation Forest)
 ├─ Revenue Forecaster         (XGBoost)
 ├─ HR Attrition Classifier    (Random Forest)
 ├─ HR Anomaly Detector        (Local Outlier Factor)
 └─ Ops Anomaly Detector       (Isolation Forest)
        │
        ▼
Scoring Engine (Weighted Composite)
        │
        ▼
Groq AI Layer (LLaMA 3 — Free)
        │
        ▼
Streamlit Dashboard → End User
```

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/your-username/business-health-monitor.git
cd business-health-monitor
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY (free at groq.com)
# Leave DB_URL empty to use SQLite (recommended for demo)
```

### 3. Initialize the database

```bash
python -c "
from data.pipeline.db_connection import get_connection
import sqlite3
conn = get_connection()
with open('sql/schema.sql') as f:
    conn.executescript(f.read())
conn.commit()
conn.close()
print('Database initialized.')
"
```

### 4. Run the full pipeline

```bash
python run_pipeline.py --mode full
```

### 5. Launch the dashboard

```bash
streamlit run app/dashboard.py
```

---

## 🗂️ Repository Structure

```
business_health_monitor/
├── run_pipeline.py              # Master orchestrator
├── config.yaml                  # All configuration
├── requirements.txt
├── .env.example
│
├── data/
│   ├── generators/
│   │   ├── finance_generator.py
│   │   ├── hr_generator.py
│   │   └── ops_generator.py
│   └── pipeline/
│       ├── db_connection.py
│       └── ingest.py
│
├── sql/
│   ├── schema.sql               # All 8 table definitions
│   ├── seed_data.sql
│   ├── migrations/
│   └── queries/                 # Named SQL query files
│
├── ml/
│   ├── models/                  # 5 ML models
│   ├── scoring/                 # Scoring engine
│   ├── ai_layer/                # Groq + LLaMA 3
│   └── utils/                   # Preprocessing & model store
│
├── app/
│   ├── dashboard.py             # Streamlit entry point
│   ├── pages/                   # 5 dashboard pages
│   ├── components/              # Reusable UI components
│   └── db/                      # SQL query wrappers
│
└── tests/                       # Full pytest suite
```

---

## 🤖 ML Models

| # | Model | Algorithm | Target Metric |
|---|-------|-----------|--------------|
| 1 | Finance Anomaly Detector | Isolation Forest | Precision > 0.85, Recall > 0.80 |
| 2 | Revenue Forecaster | XGBoost | MAPE < 8% |
| 3 | HR Attrition Classifier | Random Forest | ROC-AUC > 0.82 |
| 4 | HR Anomaly Detector | Local Outlier Factor | Recall > 0.75 |
| 5 | Ops Anomaly Detector | Isolation Forest | Precision > 0.85, Recall > 0.80 |
| 6 | Health Scoring Engine | Weighted Composite | — |

---

## 🧪 Running Tests

```bash
pytest tests/ -v --tb=short
```

---

## 🏃 Pipeline Modes

```bash
python run_pipeline.py --mode full      # Complete end-to-end
python run_pipeline.py --mode generate  # Data generation only
python run_pipeline.py --mode ingest    # SQL ingestion only
python run_pipeline.py --mode ml        # ML models only
python run_pipeline.py --mode score     # Scoring engine only
python run_pipeline.py --mode ai        # AI report only
python run_pipeline.py --mode init-db   # Initialize DB schema
```

---

## 💰 Cost

**Zero.** This project uses:
- SQLite (free, built into Python)
- All open-source ML libraries (scikit-learn, XGBoost)
- Groq API — **free tier**, no credit card required
- Streamlit Cloud — **free tier** for public apps

---

## 📖 Tech Stack

| Category | Tool |
|----------|------|
| Language | Python 3.13 |
| Database | PostgreSQL 16 / SQLite 3 |
| ML | scikit-learn 1.5, XGBoost 2.1 |
| AI | Groq SDK + LLaMA 3 (free) |
| Dashboard | Streamlit 1.36 + Plotly 5.22 |
| Testing | pytest 8.2 |
| Deployment | Streamlit Cloud (free) |

---

**Built by Abdul Wahab** | Data Analyst · Python · SQL · ML · AI Integration  
📧 abdul00wahab1000@gmail.com
