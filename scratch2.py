from app.cf_client import get_user_submissions
subs = get_user_submissions("jaijerry23")
tag_stats = {}
for s in subs:
    for tag in s["tags"]:
        if tag not in tag_stats:
            tag_stats[tag] = {"attempts": 0, "solved": 0}
        tag_stats[tag]["attempts"] += 1
        if s["solved"]:
            tag_stats[tag]["solved"] += 1
print("DP stats:", tag_stats.get("dp", "Not found"))
print("Graphs stats:", tag_stats.get("graphs", "Not found"))
print("Math stats:", tag_stats.get("math", "Not found"))
