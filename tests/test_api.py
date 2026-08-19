"""
Tests for the FastAPI application.

Uses an in-memory SQLite database so tests run fast
and don't touch real data.
"""

import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, User, Problem, Submission, get_db
from app.main import app

# ── in-memory test DB ─────────────────────────────────────────
TEST_DB_URL = "sqlite:///./data/test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ── fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    # seed minimal data
    db = TestSession()
    db.add(User(id=1, username="test_user", skill_level=0.5))
    db.add(Problem(id=1001, difficulty="Easy", topic="Arrays"))
    db.add(Problem(id=1002, difficulty="Medium", topic="DP"))
    db.add(Problem(id=1003, difficulty="Hard", topic="Graphs"))
    db.add(Submission(user_id=1, problem_id=1001, solved=True))
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


# ── tests ─────────────────────────────────────────────────────

def test_health_check():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_users():
    resp = client.get("/users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    assert users[0]["username"] == "test_user"


def test_user_stats():
    resp = client.get("/users/1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total_attempts"] >= 1


def test_user_not_found():
    resp = client.get("/users/9999/stats")
    assert resp.status_code == 404


def test_submit():
    resp = client.post("/submit", json={
        "user_id": 1,
        "problem_id": 1002,
        "solved": False,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == 1
    assert data["problem_id"] == 1002
    assert data["solved"] is False


def test_submit_invalid_user():
    resp = client.post("/submit", json={
        "user_id": 9999,
        "problem_id": 1001,
        "solved": True,
    })
    assert resp.status_code == 404


def test_recommend():
    resp = client.get("/recommend/1?n=5")
    assert resp.status_code == 200
    recs = resp.json()
    assert isinstance(recs, list)
    # should recommend unsolved problems
    for r in recs:
        assert "id" in r
        assert "predicted_solve_probability" in r


def test_recommend_invalid_user():
    resp = client.get("/recommend/9999")
    assert resp.status_code == 404
