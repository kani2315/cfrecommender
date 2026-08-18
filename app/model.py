"""
Model loading & prediction helpers.

Loads the trained sklearn pipeline from disk and exposes
a `predict_batch()` function used by the real-time Codeforces recommender.
"""

import pathlib
import pandas as pd
import joblib

# ── paths ─────────────────────────────────────────────────────
MODEL_DIR  = pathlib.Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODEL_DIR / "logistic_model.joblib"

# ── lazy-loaded globals ──────────────────────────────────────
_pipeline = None
_last_mtime = 0.0

def split_tags(tag_str: str) -> list[str]:
    # helper to parse tags string into a list
    """Custom tokenizer for Codeforces tags. Must be in a module to be pickled correctly."""
    if not tag_str:
        return []
    return [t.strip() for t in tag_str.split(",")]

def _load():
    # loads the machine learning model from disk into memory
    """Load model pipeline, reloading if the file on disk has been updated."""
    global _pipeline, _last_mtime
    
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Run scripts/train.py first.")
        
    current_mtime = MODEL_PATH.stat().st_mtime
    
    # Reload if model isn't loaded yet OR if the file was modified since last load
    if _pipeline is None or current_mtime > _last_mtime:
        _pipeline = joblib.load(MODEL_PATH)
        _last_mtime = current_mtime
        
    return _pipeline


def predict_batch(records: list[dict]) -> list[float]:
    # predicts the win-rate probability for a batch of problems
    """
    Predict P(solve) for a batch of candidate problems for a user.

    Each record dict must have keys:
      user_rating (int), problem_rating (int), tags (str)

    Returns a list of float probabilities (same order).
    """
    if not records:
        return []
        
    pipeline = _load()

    # Convert list of dicts to a pandas DataFrame
    df = pd.DataFrame(records)
    
    # Ensure missing tags are empty strings
    if "tags" in df.columns:
        df["tags"] = df["tags"].fillna("")

    # Predict probabilities. predict_proba returns an array of shape (n_samples, n_classes)
    # where the second column (index 1) is usually the positive class (1 = Solved)
    probas = pipeline.predict_proba(df)[:, 1]
    
    return [float(p) for p in probas]
