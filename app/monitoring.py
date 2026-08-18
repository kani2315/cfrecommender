"""
Step 10 — Prometheus Monitoring.

Tracks:
  • request_count        — total HTTP requests (by method, endpoint, status)
  • request_latency      — response time histogram
  • recommendation_count — how many recommendations have been served
  • model_prediction_seconds — ML model inference time

Exposes metrics at GET /metrics.
"""

import time
from prometheus_client import (
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST,
)
from starlette.requests import Request
from starlette.responses import Response


# ── metrics ───────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

RECOMMENDATION_COUNT = Counter(
    "recommendations_served_total",
    "Total number of individual problem recommendations served",
)

MODEL_PREDICTION_TIME = Histogram(
    "model_prediction_seconds",
    "Time spent in ML model prediction",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)


# ── middleware helper ─────────────────────────────────────────

async def prometheus_middleware(request: Request, call_next):
    # middleware to track prometheus metrics for every api call
    """Starlette middleware that records request count + latency."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    # normalise path (replace numeric IDs with :id)
    path = request.url.path
    for part in path.split("/"):
        if part.isdigit():
            path = path.replace(part, ":id")

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=path,
        status=response.status_code,
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=path,
    ).observe(elapsed)

    return response


# ── /metrics endpoint ────────────────────────────────────────

async def metrics_endpoint(request: Request) -> Response:
    # exposes the metrics so prometheus can scrape them
    """Prometheus scrape endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
