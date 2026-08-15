"""
Pydantic schemas for request / response validation.
"""

from typing import Optional
from pydantic import BaseModel


# ── Problem ───────────────────────────────────────────────────

class ProblemOut(BaseModel):
    """Returned in recommendation lists."""
    id: str
    name: str
    rating: Optional[int] = None
    tags: Optional[str] = None
    predicted_solve_probability: float
    difficulty_category: str


# ── User ──────────────────────────────────────────────────────

class UserOut(BaseModel):
    handle: str
    rating: Optional[int] = None
    max_rating: Optional[int] = None
    rank: Optional[str] = None

    class Config:
        from_attributes = True
