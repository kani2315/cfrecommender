"""
Step 2 — Seed the database from data/dataset.csv.

This script:
  1. Creates all tables (if they don't exist)
  2. Reads the CSV generated in Step 1
  3. Inserts unique users, unique problems, and all submissions

Run:
  python scripts/seed_db.py
"""

import sys, pathlib

# make sure `app` package is importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
from app.database import create_tables, SessionLocal, User, Problem, Submission

CSV_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "dataset.csv"


def seed():
    if not CSV_PATH.exists():
        print("❌  dataset.csv not found — run generate_data.py first")
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    create_tables()
    db = SessionLocal()

    try:
        # ── 1. Users ─────────────────────────────────────────
        user_ids = sorted(int(x) for x in df["UserID"].unique())
        existing_users = {u.id for u in db.query(User.id).all()}
        new_users = 0
        for uid in user_ids:
            if uid not in existing_users:
                db.add(User(id=uid, username=f"user_{uid}", skill_level=0.0))
                new_users += 1
        db.commit()
        print(f"👤  Users     : {new_users} inserted  ({len(user_ids)} total)")

        # ── 2. Problems ──────────────────────────────────────
        problems_df = df.drop_duplicates(subset="ProblemID")[["ProblemID", "Difficulty", "Topic"]]
        existing_problems = {p.id for p in db.query(Problem.id).all()}
        new_problems = 0
        for _, row in problems_df.iterrows():
            pid = int(row["ProblemID"])
            if pid not in existing_problems:
                db.add(Problem(
                    id=pid,
                    difficulty=str(row["Difficulty"]),
                    topic=str(row["Topic"]),
                ))
                new_problems += 1
        db.commit()
        print(f"📝  Problems  : {new_problems} inserted  ({len(problems_df)} total)")

        # ── 3. Submissions ───────────────────────────────────
        existing_count = db.query(Submission).count()
        if existing_count > 0:
            print(f"⏭️   Submissions: skipped (already {existing_count} rows)")
        else:
            for _, row in df.iterrows():
                db.add(Submission(
                    user_id=int(row["UserID"]),
                    problem_id=int(row["ProblemID"]),
                    solved=bool(row["Solved"]),
                ))
            db.commit()
            print(f"📮  Submissions: {len(df)} inserted")

        print("\n✅  Database seeded successfully!")
        print(f"📂  DB file: {pathlib.Path('data/app.db').resolve()}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
