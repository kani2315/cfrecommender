"""
Step 1 — Generate a realistic synthetic dataset for the
Competitive Coding Recommendation System.

Dataset schema
--------------
UserID     : int   — unique learner id  (1‑50)
ProblemID  : int   — unique problem id  (1001‑1200)
Difficulty : str   — Easy / Medium / Hard
Topic      : str   — one of 8 competitive‑programming topics
Solved     : int   — 1 if the user solved it, 0 otherwise

The generation logic mimics realistic patterns:
  • Each user has a "skill level" that influences solve probability.
  • Harder problems are less likely to be solved.
  • Each user attempts a random subset of problems.
"""

import random, csv, os, pathlib

random.seed(42)

# ── configuration ──────────────────────────────────────────────
NUM_USERS = 50
PROBLEM_RANGE = (1001, 1200)          # 200 problems
MIN_ATTEMPTS = 15                     # min problems a user attempts
MAX_ATTEMPTS = 80                     # max problems a user attempts

TOPICS = [
    "Arrays", "Graphs", "DP",
    "Greedy", "Math", "Strings",
    "Trees", "Sorting",
]

DIFFICULTIES = ["Easy", "Medium", "Hard"]
DIFF_WEIGHTS = [0.40, 0.35, 0.25]     # distribution when generating problems

# base solve‑probability per difficulty (before user skill adjustment)
BASE_SOLVE_PROB = {"Easy": 0.80, "Medium": 0.55, "Hard": 0.30}

# ── build a problem catalog ───────────────────────────────────
problems = {}
for pid in range(PROBLEM_RANGE[0], PROBLEM_RANGE[1] + 1):
    diff = random.choices(DIFFICULTIES, weights=DIFF_WEIGHTS, k=1)[0]
    topic = random.choice(TOPICS)
    problems[pid] = {"difficulty": diff, "topic": topic}

# ── generate submissions ──────────────────────────────────────
rows = []
for uid in range(1, NUM_USERS + 1):
    # each user has a skill modifier in [‑0.15, +0.15]
    skill = random.uniform(-0.15, 0.15)
    n_attempts = random.randint(MIN_ATTEMPTS, MAX_ATTEMPTS)
    attempted = random.sample(list(problems.keys()), k=min(n_attempts, len(problems)))

    for pid in attempted:
        p = problems[pid]
        prob = max(0.05, min(0.95, BASE_SOLVE_PROB[p["difficulty"]] + skill))
        solved = 1 if random.random() < prob else 0
        rows.append([uid, pid, p["difficulty"], p["topic"], solved])

# ── write to CSV ──────────────────────────────────────────────
data_dir = pathlib.Path(__file__).resolve().parent.parent / "data"
data_dir.mkdir(parents=True, exist_ok=True)
out_path = data_dir / "dataset.csv"

with open(out_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["UserID", "ProblemID", "Difficulty", "Topic", "Solved"])
    writer.writerows(rows)

print(f"✅  Generated {len(rows)} submission records for {NUM_USERS} users")
print(f"📂  Saved to {out_path}")
