from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Problem

engine = create_engine("postgresql://user:password@localhost:5433/mlops")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

problems = db.query(Problem.tags).all()
tag_counts = {}
for p in problems:
    if p.tags:
        for t in p.tags.split(','):
            tag = t.strip()
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
print("Top 20 tags overall:")
for tag, count in sorted_tags[:20]:
    print(f"{tag}: {count}")
