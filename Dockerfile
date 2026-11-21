FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    OSA_EPI_ROOT=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.lock

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY sql/ ./sql/
COPY tests/ ./tests/

RUN pip install --no-build-isolation --no-deps . \
    && ruff check src tests \
    && pytest

RUN mkdir -p /app/outputs/tables /app/outputs/figures

CMD ["run-osa-pipeline"]