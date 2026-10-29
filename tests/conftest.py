"""Shared fixtures. In-memory SQLite + seeded problem catalogue."""
import sys, pathlib, pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, Problem, User, Submission


@pytest.fixture(scope="function")
def db():
    """Fresh in-memory DB per test. StaticPool keeps one connection alive."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def seeded_db(db):
    """A small catalogue spanning ratings 800-2000 with known tags."""
    problems = [
        Problem(id="P800",  name="Easy Math",   rating=800,  tags="math",          solve_count=9000),
        Problem(id="P1000", name="Greedy One",  rating=1000, tags="greedy,math",   solve_count=5000),
        Problem(id="P1100", name="DP One",      rating=1100, tags="dp",            solve_count=4000),
        Problem(id="P1200", name="DP Two",      rating=1200, tags="dp,math",       solve_count=3000),
        Problem(id="P1300", name="Graph One",   rating=1300, tags="graphs",        solve_count=2500),
        Problem(id="P1400", name="DP Three",    rating=1400, tags="dp,graphs",     solve_count=2000),
        Problem(id="P1500", name="Trees One",   rating=1500, tags="trees,dp",      solve_count=1500),
        Problem(id="P2000", name="Way Too Hard",rating=2000, tags="dp",            solve_count=200),
        Problem(id="PNULL", name="Unrated",     rating=None, tags="dp",            solve_count=100),
    ]
    db.add_all(problems)
    db.commit()
    return db


def sub(pid, tags, rating, solved):
    """Shape matching cf_client.get_user_submissions() output."""
    return {"problem_id": pid, "tags": tags, "rating": rating, "solved": solved}


@pytest.fixture
def wide_db(db):
    """Catalogue with a realistic tag vocabulary (~37 tags), like production."""
    TAGS = ["math","greedy","dp","graphs","trees","strings","sortings","binary search",
            "dfs and similar","data structures","implementation","brute force","two pointers",
            "constructive algorithms","number theory","combinatorics","bitmasks","geometry",
            "dsu","shortest paths","probabilities","hashing","games","flows","divide and conquer",
            "interactive","matrices","string suffix structures","fft","graph matchings",
            "ternary search","expression parsing","meet-in-the-middle","2-sat","chinese remainder theorem",
            "schedules","*special"]
    rows = []
    for i, tag in enumerate(TAGS):
        for j in range(6):                      # 6 problems per tag inside the band
            rows.append(Problem(id=f"W{i}_{j}", name=f"{tag} #{j}",
                                rating=1000 + (j * 60), tags=tag, solve_count=1000 + i))
    db.add_all(rows)
    db.commit()
    return db
