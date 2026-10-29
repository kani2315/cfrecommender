import sys
import os
import pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from scripts.train import load_data_from_db

def main():
    df = load_data_from_db()
    if len(df) == 0:
        print("No data found.")
        return

    # Handle missing tags
    df["tags"] = df["tags"].fillna("")
    
    # Engineer user_total_solved
    user_counts = df.groupby('user_handle').size().reset_index(name='user_total_solved')
    df = df.merge(user_counts, on='user_handle')
    
    df = df.dropna(subset=["user_rating", "problem_rating", "solved"])
    
    # Engineer user_topic_winrate
    df_tags = df[["user_handle", "tags", "solved"]].copy()
    df_tags["tag_list"] = df_tags["tags"].apply(lambda x: [t.strip() for t in x.split(",") if t.strip() and t.strip() != "*special"])
    df_exploded = df_tags.explode("tag_list")
    
    global_winrate = df["solved"].mean()
    
    tag_stats = df_exploded.groupby(["user_handle", "tag_list"]).agg(
        attempts=("solved", "count"),
        solves=("solved", "sum")
    ).reset_index()
    tag_stats["win_rate"] = tag_stats["solves"] / tag_stats["attempts"]
    
    user_tag_winrates = {}
    for _, row in tag_stats.iterrows():
        u = row["user_handle"]
        t = row["tag_list"]
        w = row["win_rate"]
        if u not in user_tag_winrates:
            user_tag_winrates[u] = {}
        user_tag_winrates[u][t] = w
        
    def get_avg_winrate(row):
        u = row["user_handle"]
        tags = [t.strip() for t in row["tags"].split(",") if t.strip() and t.strip() != "*special"]
        if not tags:
            return global_winrate
        
        rates = []
        for t in tags:
            rates.append(user_tag_winrates.get(u, {}).get(t, global_winrate))
        return sum(rates) / len(rates)
        
    df["user_topic_winrate"] = df.apply(get_avg_winrate, axis=1)
    
    # Correlation
    import pandas as pd
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    numeric_df = df[["user_rating", "problem_rating", "problem_solve_count", "user_total_solved", "user_topic_winrate", "solved"]]
    print(numeric_df.corr())

if __name__ == "__main__":
    main()
