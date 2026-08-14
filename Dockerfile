# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /app

# install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.10-slim

WORKDIR /app

# copy installed packages from builder
COPY --from=builder /install /usr/local

# copy application code
COPY . .

# create data & models dirs (may already exist in the image)
RUN mkdir -p data models

# expose the API port (Railway overrides via $PORT)
EXPOSE 8000

# run the FastAPI app via uvicorn
# Railway sets $PORT dynamically; fallback to 8000 for local dev
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
