# syntax=docker/dockerfile:1
FROM python:3.11-slim

# ── Labels ────────────────────────────────────────────────────────────────────
LABEL maintainer="ShankarAdari"
LABEL description="Binance Futures Testnet Trading Bot"
LABEL version="2.0"

# ── Environment ───────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Dependencies (cached layer) ───────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Create logs directory ─────────────────────────────────────────────────────
RUN mkdir -p logs

# ── Non-root user for security ────────────────────────────────────────────────
RUN addgroup --system botgroup && \
    adduser --system --ingroup botgroup botuser && \
    chown -R botuser:botgroup /app
USER botuser

# ── Entrypoint ────────────────────────────────────────────────────────────────
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]
