import sys
import random
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import get_db, Problem
from app import recommender

def evaluate_user(handle: str):
    print(f"--- Evaluating Baselines for user: {handle} ---")
    db = next(get_db())
    
    # 1. Fetch user stats
    user_info = recommender.get_user_info(handle)
    if not user_info:
        print(f"User {handle} not found.")
        return
        
    user_rating = user_info.get("rating", 0)
    subs = recommender.get_user_submissions(handle)
    solved_ids = {s["problem_id"] for s in subs if s["solved"]}
    user_total_solved = len(solved_ids)
    
    if not user_rating or user_rating == 0:
        if solved_ids:
            solved_probs = db.query(Problem.rating).filter(Problem.id.in_(solved_ids)).filter(Problem.rating.isnot(None)).all()
            user_rating = int(sum(p[0] for p in solved_probs) / len(solved_probs)) if solved_probs else 1000
        else:
            user_rating = 1000
            
    print(f"User Rating (or estimated): {user_rating}")
    print(f"Total Solved: {user_total_solved}")

    # Calculate tag stats
    tag_stats = {}
    for s in subs:
        for tag in s["tags"]:
            if tag not in tag_stats:
                tag_stats[tag] = {"attempts": 0, "solved": 0}
            tag_stats[tag]["attempts"] += 1
            if s["solved"]:
                tag_stats[tag]["solved"] += 1

    user_tag_winrates = {}
    for t, stats in tag_stats.items():
        if stats["attempts"] > 0:
            user_tag_winrates[t] = stats["solved"] / stats["attempts"]

    def get_avg_winrate(p_tags):
        if not p_tags: return 0.50
        tags = [t.strip() for t in p_tags.split(",") if t.strip() and t.strip() != "*special"]
        if not tags: return 0.50
        rates = [user_tag_winrates.get(t, 0.50) for t in tags]
        return sum(rates) / len(rates)

    weak_tags = recommender._get_weak_tags(subs)
    avoided_tags_dicts = recommender._get_avoided_tags(db, user_rating, tag_stats)
    avoided_tags = [t["tag"] for t in avoided_tags_dicts]

    if not weak_tags and not avoided_tags:
        print("No weak or avoided tags found.")
        return

    # Let's pick the FIRST weak tag to do our baseline comparison on
    tag_to_test = weak_tags[0] if weak_tags else avoided_tags[0]
    print(f"\nEvaluating candidates for tag: '{tag_to_test}'")

    # The SQL Filter
    cands = (
        db.query(Problem)
        .filter(Problem.rating.isnot(None))
        .filter(Problem.rating >= max(0, user_rating - 300))
        .filter(Problem.rating <= user_rating + 300)
        .filter(Problem.tags.contains(tag_to_test))
        .filter(~Problem.id.in_(solved_ids) if solved_ids else True)
        .all()
    )
    
    print(f"Candidate pool size (after SQL filter): {len(cands)}")
    
    if len(cands) < 3:
        print("Not enough candidates to compare.")
        return

    # 1. ML Model Picks (Target 0.50 for Medium)
    records = [
        {
            "user_rating":         user_rating,
            "problem_rating":      p.rating,
            "problem_solve_count": p.solve_count,
            "user_total_solved":   user_total_solved,
            "user_topic_winrate":  get_avg_winrate(p.tags),
            "tags":                p.tags,
        }
        for p in cands
    ]
    probas = recommender.predict_batch(records)
    ml_scored = []
    for p, prob in zip(cands, probas):
        ml_scored.append({
            "id": p.id,
            "name": p.name,
            "rating": p.rating,
            "tags": p.tags,
            "solve_count": p.solve_count,
            "user_topic_winrate": get_avg_winrate(p.tags),
            "prob": round(prob, 4)
        })
    ml_scored.sort(key=lambda x: abs(x["prob"] - 0.50))
    ml_picks = ml_scored[:3]

    # 2. Random Picks
    random_cands = list(cands)
    random.shuffle(random_cands)
    random_picks = random_cands[:3]

    # 3. Rating-Only Baseline (Closest to User Rating)
    rating_scored = list(cands)
    rating_scored.sort(key=lambda p: abs(p.rating - user_rating))
    rating_picks = rating_scored[:3]

    print("\n[ML MODEL PICKS (Closest to 0.50 prob)]")
    for p in ml_picks:
        print(f"  {p['id']:6} | Rating: {p['rating']:4} | Prob: {p['prob']:.3f} | Pop: {p['solve_count']:5} | WinRate: {p['user_topic_winrate']:.2f} | {p['name']} ({p['tags']})")

    print("\n[RANDOM BASELINE PICKS]")
    for p in random_picks:
        print(f"  {p.id:6} | Rating: {p.rating:4} | Pop: {p.solve_count:5} | {p.name} ({p.tags})")

    print("\n[RATING-ONLY BASELINE PICKS (Closest to User Rating)]")
    for p in rating_picks:
        print(f"  {p.id:6} | Rating: {p.rating:4} | Pop: {p.solve_count:5} | {p.name} ({p.tags})")

if __name__ == "__main__":
    evaluate_user("kani2315")
    print("\n" + "="*60 + "\n")
    evaluate_user("tourist")
