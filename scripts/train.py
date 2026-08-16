"""
Train a Logistic Regression model to predict P(solve) using real Codeforces data.

Features
--------
  • user_rating     → numerical
  • problem_rating  → numerical
  • tags            → bag of words (CountVectorizer)

Target
------
  • Solved  (0 or 1)

Outputs
-------
  • models/logistic_model.joblib      — trained pipeline

Run:
  python scripts/train.py
"""

import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report,
)

from app.model import split_tags
from app.database import SessionLocal, User, Problem, Submission

# ── paths ─────────────────────────────────────────────────────
BASE      = pathlib.Path(__file__).resolve().parent.parent
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "logistic_model.joblib"


def load_data_from_db():
    print("Fetching training data from database...")
    db = SessionLocal()
    try:
        # Join Submissions, Users, and Problems to build our dataset
        query = (
            db.query(
                User.rating.label("user_rating"),
                Problem.rating.label("problem_rating"),
                Problem.tags,
                Submission.solved
            )
            .join(Submission, User.handle == Submission.user_handle)
            .join(Problem, Problem.id == Submission.problem_id)
            # Filter out records where rating is missing, as they are crucial features
            .filter(Problem.rating.isnot(None))
            .filter(User.rating.isnot(None))
        )
        
        df = pd.read_sql(query.statement, db.bind)
        return df
    finally:
        db.close()


def train():
    # ── 1. Load data ──────────────────────────────────────────
    df = load_data_from_db()
    
    if len(df) == 0:
        print("❌ Error: No training data found in database. Run fetch_cf_data.py first.")
        return

    # Handle missing tags (replace with empty string)
    df["tags"] = df["tags"].fillna("")
    
    print(f"📂  Loaded {len(df)} submission records for training.")
    
    # ── 2. Prepare feature matrix ─────────────────────────────
    # We drop NaN values just in case
    df = df.dropna(subset=["user_rating", "problem_rating", "solved"])
    
    X = df[["user_rating", "problem_rating", "tags"]]
    y = df["solved"].astype(int)

    # ── 3. Train / test split ─────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )
    print(f"🔀  Split → train={len(X_train)}  test={len(X_test)}")

    # ── 4. Build pipeline ─────────────────────────────────────
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", ["user_rating", "problem_rating"]),
            ("cat", CountVectorizer(tokenizer=split_tags, token_pattern=None), "tags"),
        ]
    )

    pipeline = Pipeline([
        ("pre",   preprocessor),
        ("model", LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')),
    ])

    # ── 5. Fit ────────────────────────────────────────────────
    pipeline.fit(X_train, y_train)
    print("✅  Model trained")

    # ── 6. Evaluate ───────────────────────────────────────────
    y_pred = pipeline.predict(X_test)

    print("\n" + "=" * 50)
    print("📊  TEST SET METRICS")
    print("=" * 50)
    print(f"  Accuracy  : {accuracy_score(y_test, y_pred):.3f}")
    print(f"  Precision : {precision_score(y_test, y_pred):.3f}")
    print(f"  Recall    : {recall_score(y_test, y_pred):.3f}")
    print(f"  F1 Score  : {f1_score(y_test, y_pred):.3f}")
    print("\n" + classification_report(y_test, y_pred, target_names=["Not Solved", "Solved"]))

    # ── 7. Save artifacts ─────────────────────────────────────
    joblib.dump(pipeline, MODEL_PATH)

    print(f"💾  Model saved → {MODEL_PATH}")
    print("\n✅  Training complete! Model is ready for real-time recommendations.")


if __name__ == "__main__":
    train()
