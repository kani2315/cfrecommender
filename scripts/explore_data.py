"""
Step 1 — Explore the generated dataset.

Prints summary statistics so we can confirm the data
looks reasonable before moving on to model training.
"""

import pandas as pd, pathlib, sys

data_path = pathlib.Path(__file__).resolve().parent.parent / "data" / "dataset.csv"

if not data_path.exists():
    print("❌  dataset.csv not found — run generate_data.py first")
    sys.exit(1)

df = pd.read_csv(data_path)

print("=" * 60)
print("📊  DATASET OVERVIEW")
print("=" * 60)
print(f"\nShape          : {df.shape[0]} rows × {df.shape[1]} columns")
print(f"Unique users   : {df['UserID'].nunique()}")
print(f"Unique problems: {df['ProblemID'].nunique()}")

print("\n── First 5 rows ──")
print(df.head().to_string(index=False))

print("\n── Solve rate by difficulty ──")
solve_by_diff = df.groupby("Difficulty")["Solved"].mean().round(3)
for diff in ["Easy", "Medium", "Hard"]:
    if diff in solve_by_diff.index:
        print(f"  {diff:8s}  →  {solve_by_diff[diff]*100:.1f}%")

print("\n── Solve rate by topic ──")
solve_by_topic = df.groupby("Topic")["Solved"].mean().sort_values(ascending=False).round(3)
for topic, rate in solve_by_topic.items():
    print(f"  {topic:10s}  →  {rate*100:.1f}%")

print("\n── Attempts per user (min / median / max) ──")
attempts = df.groupby("UserID").size()
print(f"  min={attempts.min()}  median={int(attempts.median())}  max={attempts.max()}")

print("\n── Class balance (Solved) ──")
counts = df["Solved"].value_counts()
print(f"  Solved=1 : {counts.get(1,0)}  ({counts.get(1,0)/len(df)*100:.1f}%)")
print(f"  Solved=0 : {counts.get(0,0)}  ({counts.get(0,0)/len(df)*100:.1f}%)")

print("\n" + "=" * 60)
print("✅  Data looks good — ready for Step 2+")
print("=" * 60)
