"""
FastAPI Backend Application for Codeforces Recommender.

Endpoints
---------
GET  /                          → health check
GET  /recommend/{handle}        → top-N recommended problems for a Codeforces handle
GET  /users                     → list all locally cached users
GET  /metrics                   → Prometheus metrics
"""

import sys, pathlib, time, os, asyncio, subprocess

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import create_tables, get_db, User
from app.schemas import ProblemOut, UserOut
from app.recommender import recommend
from app.monitoring import prometheus_middleware, metrics_endpoint, RECOMMENDATION_COUNT

# ── initialise ────────────────────────────────────────────────
app = FastAPI(
    title="Codeforces ML Recommender",
    description="AI-powered Codeforces problem recommendations using real-time API.",
    version="2.0.0",
)

# allow all origins for local dev (will be tightened in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics middleware
app.middleware("http")(prometheus_middleware)
app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], tags=["Monitoring"])


async def background_scheduler():
    # loops forever in the background to keep the ML model fresh
    while True:
        try:
            print("🚀 Starting background ML training task...")
            subprocess.run(["python", "scripts/fetch_cf_data.py"], check=True)
            subprocess.run(["python", "scripts/train.py"], check=True)
            print("✅ Background training complete. Sleeping for 24 hours.")
        except Exception as e:
            print(f"❌ Error in background scheduler: {e}")
        await asyncio.sleep(86400)  # wait 24 hours before retraining

@app.on_event("startup")
async def on_startup():
    # runs when the server boots up
    """Create tables on first run (idempotent)."""
    create_tables()
    asyncio.create_task(background_scheduler())


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    # tracks how long each api request takes
    """Attach X-Process-Time header to every response (monitoring)."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    return response


# ══════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════

@app.get("/recommend/{handle}", tags=["Recommendations"], response_model=list[ProblemOut])
def get_recommendations(
    handle: str,
    n: int = Query(default=10, ge=1, le=50, description="Number of recommendations"),
    db: Session = Depends(get_db),
):
    # api endpoint that returns problem recommendations for a user
    """
    Return the top-N recommended problems for a Codeforces user in real-time.

    1. Fetches live submissions to find weak tags.
    2. Scores unsolved candidate problems with the ML model.
    3. Ranks by the *zone of proximal development* (P(solve) ≈ 0.50).
    """
    try:
        recs = recommend(db, handle=handle, n=n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    RECOMMENDATION_COUNT.inc(len(recs))
    return recs


@app.get("/users", tags=["Users"], response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    # diagnostic endpoint to list users in the local db
    """Return all locally cached users from the database."""
    return db.query(User).order_by(User.handle).all()

# Mount frontend files at the root
# Note: Mount this LAST so it doesn't override the /recommend and /metrics routes
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend"), html=True), name="frontend")
