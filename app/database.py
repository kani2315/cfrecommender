"""
Database connection & ORM models for Codeforces Recommendation System.

Tables
------
users        : handle (PK), rating, max_rating, rank
problems     : id (PK), name, rating, tags (comma-separated string)
submissions  : id, user_handle (FK), problem_id (FK), solved, submitted_at

Reads DATABASE_URL from .env (via python-dotenv).
"""

import os, pathlib
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, create_engine,
)
from sqlalchemy.orm import (
    declarative_base, relationship, sessionmaker,
)

# ── load .env from project root ──────────────────────────────
_env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── connection ────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

# SQLite requires check_same_thread=False for FastAPI's async usage
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,   # auto-reconnect stale PostgreSQL connections
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── ORM models ────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    handle     = Column(String(100), primary_key=True, index=True)
    rating     = Column(Integer, nullable=True)
    max_rating = Column(Integer, nullable=True)
    rank       = Column(String(50), nullable=True)

    submissions = relationship("Submission", back_populates="user")

    def __repr__(self):
        return f"<User handle={self.handle} rating={self.rating}>"


class Problem(Base):
    __tablename__ = "problems"

    # id will be contestId + index (e.g. "1553A")
    id     = Column(String(50), primary_key=True, index=True)
    name   = Column(String(200), nullable=False)
    rating = Column(Integer, nullable=True)     # problem difficulty rating (can be missing)
    tags   = Column(String(500), nullable=True) # comma-separated list of tags

    submissions = relationship("Submission", back_populates="problem")

    def __repr__(self):
        return f"<Problem id={self.id} rating={self.rating}>"


class Submission(Base):
    __tablename__ = "submissions"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_handle  = Column(String(100), ForeignKey("users.handle"), nullable=False)
    problem_id   = Column(String(50), ForeignKey("problems.id"), nullable=False)
    solved       = Column(Boolean, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    user    = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")

    def __repr__(self):
        status = "✓" if self.solved else "✗"
        return f"<Submission user={self.user_handle} problem={self.problem_id} {status}>"


# ── helpers ───────────────────────────────────────────────────

def create_tables():
    """Create all tables (safe to call multiple times)."""
    # creates the postgres tables if they don't exist
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session, then closes it."""
    # opens a db session and closes it when done
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
