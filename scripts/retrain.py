"""
Step 11 — Automated Retraining Pipeline.

This script:
  1. Exports the latest submissions from the database to CSV
  2. Retrains the Logistic Regression model on the fresh data
  3. Evaluates and saves the new model artifacts
  4. Can be run manually or via a cron job / scheduler

Usage:
  # Manual
  python scripts/retrain.py

  # Cron (retrain every day at 2 AM)
  # 0 2 * * * cd /app && python scripts/retrain.py >> logs/retrain.log 2>&1
"""

import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
from datetime import datetime

from app.database import SessionLocal, create_tables, Submission, Problem

BASE      = pathlib.Path(__file__).resolve().parent.parent
CSV_PATH  = BASE / "data" / "dataset.csv"
LOG_DIR   = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)


def export_latest_data() -> pd.DataFrame:
    """Pull all submissions from the DB and build training CSV."""
    create_tables()
    db = SessionLocal()

    try:
        subs = db.query(Submission).all()
        if not subs:
            print("⚠️  No submissions in database — nothing to retrain on")
            sys.exit(0)

        # get problem metadata
        problems = {p.id: p for p in db.query(Problem).all()}

        rows = []
        for s in subs:
            p = problems.get(s.problem_id)
            if p is None:
                continue
            rows.append({
                "UserID":     s.user_id,
                "ProblemID":  s.problem_id,
                "Difficulty": p.difficulty,
                "Topic":      p.topic,
                "Solved":     int(s.solved),
            })

        df = pd.DataFrame(rows)
        # save updated CSV
        df.to_csv(CSV_PATH, index=False)
        print(f"📂  Exported {len(df)} rows to {CSV_PATH.name}")
        return df

    finally:
        db.close()


def retrain():
    """Full retrain cycle: export → train → evaluate → save."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"🔄  RETRAIN PIPELINE — {timestamp}")
    print(f"{'='*60}\n")

    # Step 1: export fresh data from DB
    print("── Step 1: Exporting data from database ──")
    export_latest_data()

    # Step 2: retrain (reuse existing train.py logic)
    print("\n── Step 2: Training new model ──")
    from scripts.train import train
    train()

    # Step 3: log
    log_file = LOG_DIR / "retrain.log"
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] Retrain completed successfully\n")

    print(f"\n{'='*60}")
    print(f"✅  Retrain pipeline complete!")
    print(f"📝  Logged to {log_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    retrain()
