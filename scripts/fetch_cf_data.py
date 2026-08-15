"""
Fetch real problemset and user submissions from Codeforces API
and store them in the local database.

This will replace the synthetic data generation script.
"""

import sys, pathlib, time, requests
from typing import List, Dict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, create_tables, Problem, User, Submission

# Number of active users to fetch submissions for training
NUM_USERS = 50

def fetch_problems(db):
    print("Fetching Codeforces problemset...")
    url = "https://codeforces.com/api/problemset.problems"
    response = requests.get(url)
    data = response.json()
    
    if data["status"] != "OK":
        print("Failed to fetch problems:", data.get("comment"))
        return

    problems_data = data["result"]["problems"]
    
    # Optional: We could also fetch problem statistics to get solve counts,
    # but we just need rating and tags for now.
    
    # We now delete everything in main() beforehand
    
    count = 0
    for p in problems_data:
        # Some problems don't have a rating (e.g. unrated contests or very old ones)
        if "rating" not in p:
            continue
            
        pid = f"{p['contestId']}{p['index']}"
        tags = ",".join(p.get("tags", []))
        
        problem_obj = Problem(
            id=pid,
            name=p["name"],
            rating=p["rating"],
            tags=tags
        )
        db.add(problem_obj)
        count += 1
        
    db.commit()
    print(f"✅ Inserted {count} problems with ratings into DB.")


def fetch_users_and_submissions(db):
    print("Fetching active Codeforces users...")
    url = "https://codeforces.com/api/user.ratedList?activeOnly=true"
    response = requests.get(url)
    data = response.json()
    
    if data["status"] != "OK":
        print("Failed to fetch users:", data.get("comment"))
        return
        
    users_data = data["result"]
    # Take a sample of users from different rating ranges for variety
    # Here we just take the first NUM_USERS for simplicity
    selected_users = users_data[:NUM_USERS]
    
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
            sub_res = requests.get(sub_url)
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
