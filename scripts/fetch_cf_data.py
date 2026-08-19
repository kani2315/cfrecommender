"""
Fetch real problemset and user submissions from Codeforces API
and store them in the local database.

This will replace the synthetic data generation script.
"""

import sys, pathlib, time, requests, random
from typing import List, Dict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, create_tables, Problem, User, Submission

# Number of active users to fetch submissions for training
NUM_USERS = 50

def fetch_problems(db):
    print("Fetching Codeforces problemset...")
    url = "https://codeforces.com/api/problemset.problems"
    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Codeforces API: {e}")
        return
        
    data = response.json()
    
    if data["status"] != "OK":
        print("Failed to fetch problems:", data.get("comment"))
        return

    problems_data = data["result"]["problems"]
    stats_data = data["result"]["problemStatistics"]
    
    # Map problem stats (solvedCount)
    stats_map = {}
    for stat in stats_data:
        pid = f"{stat['contestId']}{stat['index']}"
        stats_map[pid] = stat.get("solvedCount", 0)
    
    count = 0
    for p in problems_data:
        # Some problems don't have a rating (e.g. unrated contests or very old ones)
        if "rating" not in p:
            continue
            
        pid = f"{p['contestId']}{p['index']}"
        tags = ",".join(p.get("tags", []))
        solve_count = stats_map.get(pid, 0)
        
        problem_obj = Problem(
            id=pid,
            name=p["name"],
            rating=p["rating"],
            tags=tags,
            solve_count=solve_count
        )
        db.add(problem_obj)
        count += 1
        
    db.commit()
    print(f"✅ Inserted {count} problems with ratings into DB.")


def fetch_users_and_submissions(db):
    print("Fetching active Codeforces users...")
    url = "https://codeforces.com/api/user.ratedList?activeOnly=true"
    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Codeforces API: {e}")
        return
        
    data = response.json()
    
    if data["status"] != "OK":
        print("Failed to fetch users:", data.get("comment"))
        return
        
    users_data = data["result"]
    
    # ── Stratified Sampling ─────────────────────────────────────
    buckets = {
        "beginner": [],   # < 1200
        "pupil": [],      # 1200 - 1399
        "specialist": [], # 1400 - 1599
        "expert": [],     # 1600 - 1899
        "advanced": []    # >= 1900
    }
    
    for u in users_data:
        r = u.get("rating", 0)
        if r < 1200:
            buckets["beginner"].append(u)
        elif r < 1400:
            buckets["pupil"].append(u)
        elif r < 1600:
            buckets["specialist"].append(u)
        elif r < 1900:
            buckets["expert"].append(u)
        else:
            buckets["advanced"].append(u)
            
    users_per_bucket = NUM_USERS // 5
    selected_users = []
    
    for bucket_name, bucket_users in buckets.items():
        if len(bucket_users) >= users_per_bucket:
            sampled = random.sample(bucket_users, users_per_bucket)
        else:
            sampled = bucket_users # Fallback if somehow not enough
        selected_users.extend(sampled)
        
    print(f"Sampled {len(selected_users)} users across {len(buckets)} skill tiers.")
    
    # Submissions and Users are now deleted in main() beforehand
    
    valid_pids = {p.id for p in db.query(Problem.id).all()}
    
    print(f"Fetching submissions for {len(selected_users)} users...")
    
    sub_count = 0
    for i, u in enumerate(selected_users):
        handle = u["handle"]
        user_obj = User(
            handle=handle,
            rating=u.get("rating", 0),
            max_rating=u.get("maxRating", 0),
            rank=u.get("rank", "")
        )
        db.add(user_obj)
        db.commit()
        
        # Fetch submissions
        # We only care about normal problem submissions (not gym)
        sub_url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=1000"
        try:
            sub_res = requests.get(sub_url, timeout=15)
            sub_data = sub_res.json()
            if sub_data["status"] == "OK":
                for sub in sub_data["result"]:
                    if "contestId" in sub["problem"]:
                        pid = f"{sub['problem']['contestId']}{sub['problem']['index']}"
                        if pid in valid_pids:
                            solved = sub["verdict"] == "OK"
                            
                            submission_obj = Submission(
                                user_handle=handle,
                                problem_id=pid,
                                solved=solved,
                                # Using default submitted_at for simplicity
                            )
                            db.add(submission_obj)
                            sub_count += 1
        except Exception as e:
            print(f"Error fetching submissions for {handle}: {e}")
            
        # Respect rate limits (1 request per 0.2s, wait a bit longer to be safe)
        time.sleep(0.5)
        
        if (i+1) % 10 == 0:
            print(f"Processed {i+1}/{len(selected_users)} users...")
            
    db.commit()
    print(f"✅ Inserted {len(selected_users)} users and {sub_count} submissions into DB.")


def main():
    print("Creating tables if they don't exist...")
    create_tables()
    
    db = SessionLocal()
    try:
        # Clear out old data in the correct order to respect foreign keys
        print("Clearing old data...")
        db.query(Submission).delete()
        db.query(User).delete()
        db.query(Problem).delete()
        db.commit()

        fetch_problems(db)
        fetch_users_and_submissions(db)
        print("\n✅ Data collection complete! DB is ready for ML training.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
