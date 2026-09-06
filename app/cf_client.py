# codeforces api client

import requests
from typing import List, Dict, Set

# Base Codeforces API URL
CF_API_BASE = "https://codeforces.com/api"


def get_user_info(handle:str)->dict:
    # profile of userr
    url = f"{CF_API_BASE}/user.info?handles={handle}"
    try:
        res=requests.get(url, timeout=10)
        data=res.json()
        if data.get("status") == "OK" and data.get("result"):
            user_data = data["result"][0] #ignore the status and brackets of dict
            return {
                "handle": user_data.get("handle"),
                "rating": user_data.get("rating", 0)  #give 0 for unrated
            }
        else:
            print(f"Error fetching CF user info: {data.get('comment')}")
            return None
    except Exception as e:
        print(f"Exception fetching CF user info: {e}")
        return None


def get_user_submissions(handle: str) -> List[Dict]:
    # submissions of userrr
    url = f"{CF_API_BASE}/user.status?handle={handle}"
    try:
        res=requests.get(url, timeout=15)
        data=res.json()
        if data.get("status") != "OK":
            print(f"Error fetching CF submissions: {data.get('comment')}")
            return []
        submissions = data.get("result", [])
        parsed_submissions=[]
        for sub in submissions:
            # ignore prob with no contest id
            if "problem" in sub and "contestId" in sub["problem"]:
                p = sub["problem"]
                pid =f"{p['contestId']}{p['index']}"
                
                parsed_submissions.append({
                    "problem_id": pid,
                    "tags": p.get("tags", []),
                    "rating": p.get("rating"),
                    "solved": sub.get("verdict") == "OK"
                })
                
        return parsed_submissions
        
    except Exception as e:
        print(f"Exception fetching CF submissions: {e}")
        return []


def get_solved_problem_ids(handle:str)->Set[str]:
    # to get the submitted prob
    """Return a set of problem IDs that the user has already solved."""
    subs = get_user_submissions(handle)
    solved = {s["problem_id"] for s in subs if s["solved"]}
    return solved
