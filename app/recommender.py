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
            if tag == '*special': continue
            if tag not in tag_stats:
                tag_stats[tag] = {"attempts": 0, "solved": 0}
            tag_stats[tag]["attempts"] += 1
            if s["solved"]:
                tag_stats[tag]["solved"] += 1

    if not tag_stats:
        return []

    topic_list = []
    for tag, stats in tag_stats.items():
        if stats["attempts"] > 0:
            win_rate = stats["solved"] / stats["attempts"]
            topic_list.append({
                "tag": tag,
                "attempts": stats["attempts"],
                "solved": stats["solved"],
                "win_rate": round(win_rate, 2)
            })
            
    topic_list.sort(key=lambda x: (x["win_rate"], x["solved"]), reverse=True)
    reliable_topics = [t for t in topic_list if t["attempts"] >= 5]
    if not reliable_topics:
        reliable_topics = topic_list
        
    weak_topics = reliable_topics[-5:] if len(reliable_topics) > 5 else []
    
    return [t["tag"] for t in weak_topics]

def _get_avoided_tags(db: Session, user_rating: int, tag_stats: dict) -> list[str]:
    # query all tags for problems in range
    problems_in_range = db.query(Problem.tags).filter(
        Problem.rating >= max(0, user_rating - 300),
        Problem.rating <= user_rating + 300,
        Problem.tags.isnot(None)
    ).all()
    
    tag_counts = {}
    for p in problems_in_range:
        if p.tags:
            for t in p.tags.split(','):
                tag = t.strip()
                if tag == '*special': continue
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
    avoided = []
    for tag, db_count in tag_counts.items():
        user_attempts = tag_stats.get(tag, {}).get("attempts", 0)
        # Avoidance ratio: how common is this globally vs how often the user attempts it
        avoidance_score = db_count / (user_attempts + 1)
        avoided.append((tag, avoidance_score))
        
    # sort by avoidance score descending so the most avoided popular topics come first
    avoided.sort(key=lambda x: x[1], reverse=True)
    
    return [x[0] for x in avoided]


def recommend(db: Session, handle: str, n: int = DEFAULT_N) -> list[dict]:
    # main logic to find and rank the best practice problems
    # get user data
    user_info = get_user_info(handle)
    if not user_info:
        raise ValueError(f"Could not find Codeforces user: {handle}")
        
    user_rating = user_info.get("rating", 0)
    subs = get_user_submissions(handle)
    
    solved_ids = {s["problem_id"] for s in subs if s["solved"]}
    user_total_solved = len(solved_ids)
    
    # 1. Handle Unrated User Cold Start
    if not user_rating or user_rating == 0:
        if solved_ids:
            # Estimate rating based on average rating of solved problems
            solved_probs = db.query(Problem.rating).filter(Problem.id.in_(solved_ids)).filter(Problem.rating.isnot(None)).all()
            if solved_probs:
                user_rating = int(sum(p[0] for p in solved_probs) / len(solved_probs))
            else:
                user_rating = 1000 # default fallback
        else:
            user_rating = 1000 # complete beginner fallback
            
    weak_tags = _get_weak_tags(subs)
    
    tag_stats = {}
    for s in subs:
        for tag in s["tags"]:
            if tag not in tag_stats:
                tag_stats[tag] = {"attempts": 0, "solved": 0}
            tag_stats[tag]["attempts"] += 1
            if s["solved"]:
                tag_stats[tag]["solved"] += 1
                
    avoided_tags = _get_avoided_tags(db, user_rating, tag_stats)

    def score_candidates(cands, target_prob):
        if not cands: return []
        records = [
            {
                "user_rating":         user_rating,
                "problem_rating":      p.rating,
                "problem_solve_count": p.solve_count,
                "user_total_solved":   user_total_solved,
                "tags":                p.tags,
            }
            for p in cands
        ]
        probas = predict_batch(records)
        scored = []
        for p, prob in zip(cands, probas):
            scored.append({
                "id":         p.id,
                "name":       p.name,
                "rating":     p.rating,
                "tags":       p.tags,
                "predicted_solve_probability": round(prob, 4),
            })
        scored.sort(key=lambda x: abs(x["predicted_solve_probability"] - target_prob))
        return scored

    seen = set()
    improve_these = []
    for tag in weak_tags:
        cands = (
            db.query(Problem)
            .filter(Problem.rating.isnot(None))
            .filter(Problem.rating >= max(0, user_rating - 300))
            .filter(Problem.rating <= user_rating + 300)
            .filter(Problem.tags.contains(tag))
            .filter(~Problem.id.in_(solved_ids) if solved_ids else True)
            .all()
        )
        cands = [c for c in cands if c.id not in seen]
        scored = score_candidates(cands, 0.50)
        selected = scored[:3]
        for x in selected:
            x["difficulty_category"] = "Let's Improve These"
            seen.add(x["id"])
            improve_these.append(x)
            
    comfort_zone = []
    for tag in avoided_tags:
        cands = (
            db.query(Problem)
            .filter(Problem.rating.isnot(None))
            .filter(Problem.rating >= max(0, user_rating - 300))
            .filter(Problem.rating <= user_rating + 300)
            .filter(Problem.tags.contains(tag))
            .filter(~Problem.id.in_(solved_ids) if solved_ids else True)
            .all()
        )
        cands = [c for c in cands if c.id not in seen]
        scored = score_candidates(cands, 0.75)
        selected = scored[:3]
        for x in selected:
            x["difficulty_category"] = "Step Out of Your Comfort Zone"
            seen.add(x["id"])
            comfort_zone.append(x)
            
    # Interleave them for a good mix when filter is "All"
    result = []
    for i in range(max(len(improve_these), len(comfort_zone))):
        if i < len(improve_these): result.append(improve_these[i])
        if i < len(comfort_zone): result.append(comfort_zone[i])
        
    return result

def analyze_user(db: Session, handle: str) -> dict:
    """Calculates detailed statistics for the Profile Analysis Dashboard."""
    user_info = get_user_info(handle)
    if not user_info:
        raise ValueError(f"Could not find Codeforces user: {handle}")
        
    user_rating = user_info.get("rating", 0)
    subs = get_user_submissions(handle)
    
    solved_ids = {s["problem_id"] for s in subs if s["solved"]}
    
    if not user_rating or user_rating == 0:
        if solved_ids:
            solved_probs = db.query(Problem.rating).filter(Problem.id.in_(solved_ids)).filter(Problem.rating.isnot(None)).all()
            if solved_probs:
                user_rating = int(sum(p[0] for p in solved_probs) / len(solved_probs))
            else:
                user_rating = 1000
        else:
            user_rating = 1000
            
    rating_stats = {}
    seen_solved = set()
    for s in subs:
        if s["solved"] and s["problem_id"] not in seen_solved:
            seen_solved.add(s["problem_id"])
            r = s.get("rating")
            if r:
                r_str = str(r)
                rating_stats[r_str] = rating_stats.get(r_str, 0) + 1
                
    tag_stats = {}
    for s in subs:
        for tag in s["tags"]:
            if tag == '*special': continue
            if tag not in tag_stats:
                tag_stats[tag] = {"attempts": 0, "solved": 0}
            tag_stats[tag]["attempts"] += 1
            if s["solved"]:
                tag_stats[tag]["solved"] += 1
                
    topic_list = []
    for tag, stats in tag_stats.items():
        if stats["attempts"] > 0:
            win_rate = stats["solved"] / stats["attempts"]
            topic_list.append({
                "tag": tag,
                "attempts": stats["attempts"],
                "solved": stats["solved"],
                "win_rate": round(win_rate, 2)
            })
            
    topic_list.sort(key=lambda x: (x["win_rate"], x["solved"]), reverse=True)
    reliable_topics = [t for t in topic_list if t["attempts"] >= 5]
    if not reliable_topics:
        reliable_topics = topic_list
        
    strong_topics = reliable_topics[:5]
    weak_topics = reliable_topics[-5:] if len(reliable_topics) > 5 else []
    weak_topics.reverse()
    
    avoided_tags = _get_avoided_tags(db, user_rating, tag_stats)[:5]
    
    return {
        "handle": handle,
        "current_rating": user_rating,
        "rating_range": [max(0, user_rating - 300), user_rating + 300],
        "rating_stats": rating_stats,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "avoided_topics": avoided_tags[:5]
    }
