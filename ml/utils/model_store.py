"""
ml/utils/model_store.py
────────────────────────────────────────────────────────────────────────────────
Model persistence using joblib.
Saves and loads trained sklearn / XGBoost models to ml/saved/.
"""

import logging
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

SAVE_DIR = Path("ml/saved")
SAVE_DIR.mkdir(parents=True, exist_ok=True)


def save_model(model: Any, name: str) -> Path:
    """
    Serialize a model to ml/saved/<name>.joblib.

    Parameters
    ----------
    model : any sklearn / XGBoost model or dict of model + metadata
    name : logical model name (e.g. 'finance_anomaly')

    Returns
    -------
    Path to saved file.
    """
    path = SAVE_DIR / f"{name}.joblib"
    joblib.dump(model, path)
    logger.info(f"Model saved → {path}")
    return path


def load_model(name: str) -> Any:
    """
    Deserialize a model from ml/saved/<name>.joblib.

    Raises FileNotFoundError if model has not been trained yet.
    """
    path = SAVE_DIR / f"{name}.joblib"
    if not path.exists():
        raise FileNotFoundError(
            f"Model '{name}' not found at {path}. "
            "Run the pipeline (python run_pipeline.py --mode ml) first."
        )
    model = joblib.load(path)
    logger.info(f"Model loaded ← {path}")
    return model


def model_exists(name: str) -> bool:
    """Return True if a saved model file exists for the given name."""
    return (SAVE_DIR / f"{name}.joblib").exists()
