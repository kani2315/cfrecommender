# recommender logic

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import Problem
from app.model import predict_batch
from app.cf_client import get_user_info, get_user_submissions


DEFAULT_N          = 10       
SWEET_SPOT_LOW     = 0.30     
SWEET_SPOT_HIGH    = 0.70     


def _get_weak_tags(subs: list[dict]) -> list[str]:
    # calculates which topics the user struggles with the most
    """Analyze live submissions and return tags where the user is weak."""
    tag_stats = {}
    
    for s in subs:
        for tag in s["tags"]:
            if tag not in tag_stats:
                tag_stats[tag] = {"attempts": 0, "solved": 0}
            tag_stats[tag]["attempts"] += 1
            if s["solved"]:
                tag_stats[tag]["solved"] += 1

    if not tag_stats:
        return []

    overall_rate = sum(t["solved"] for t in tag_stats.values()) / max(sum(t["attempts"] for t in tag_stats.values()), 1)
    
    weak_tags = []
    for tag, stats in tag_stats.items():
        rate = stats["solved"] / stats["attempts"]
        if rate < overall_rate:
            weak_tags.append(tag)
            
    return weak_tags


def recommend(db: Session, handle: str, n: int = DEFAULT_N) -> list[dict]:
    # main logic to find and rank the best practice problems
    # get user data
    user_info = get_user_info(handle)
    if not user_info:
        raise ValueError(f"Could not find Codeforces user: {handle}")
        
    user_rating = user_info["rating"]
    subs = get_user_submissions(handle)
    
    solved_ids = {s["problem_id"] for s in subs if s["solved"]}
    weak_tags = _get_weak_tags(subs)

    # 2. Candidate problems (unsolved)
    # We try to find unsolved problems in their weak tags first
    candidates = []
    
    if weak_tags:
        # Build an OR condition to find problems containing ANY of the weak tags
        tag_filters = [Problem.tags.contains(tag) for tag in weak_tags]
        
        candidates = (
            db.query(Problem)
            .filter(Problem.rating.isnot(None)) # must have rating for ML model
            .filter(or_(*tag_filters))
            .filter(~Problem.id.in_(solved_ids) if solved_ids else True)
            .all()
        )
        
    # fallback: if not enough candidates, fetch generic unsolved problems
    if len(candidates) < n:
        all_unsolved = (
            db.query(Problem)
            .filter(Problem.rating.isnot(None))
            .filter(~Problem.id.in_(solved_ids) if solved_ids else True)
            .all()
        )
        seen = {c.id for c in candidates}
        for p in all_unsolved:
            if p.id not in seen:
                candidates.append(p)
                seen.add(p.id)

    if not candidates:
        return []

    # 3. Score candidates with the ML model
    records = [
        {
            "user_rating":    user_rating,
            "problem_rating": p.rating,
            "tags":           p.tags,
        }
        for p in candidates
    ]
    
    probas = predict_batch(records)

    scored = []
    for p, prob in zip(candidates, probas):
        scored.append({
            "id":         p.id,
            "name":       p.name,
            "rating":     p.rating,
            "tags":       p.tags,
            "predicted_solve_probability": round(prob, 4),
        })

    # get dynamic targets so everyone gets different problems
    # easy target 0.75
    scored.sort(key=lambda x: abs(x["predicted_solve_probability"] - 0.75))
    easy = scored[:10]
    for x in easy: x["difficulty_category"] = "Easy"
    
    # Medium (Target P = 0.50)
    remaining = scored[10:]
    remaining.sort(key=lambda x: abs(x["predicted_solve_probability"] - 0.50))
    medium = remaining[:10]
    for x in medium: x["difficulty_category"] = "Medium"
    
    # Hard (Target P = 0.25)
    remaining = remaining[10:]
    remaining.sort(key=lambda x: abs(x["predicted_solve_probability"] - 0.25))
    hard = remaining[:10]
    for x in hard: x["difficulty_category"] = "Hard"
    
    return easy + medium + hard
