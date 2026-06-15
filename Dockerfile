# SmartRiver — single container: React UI + FastAPI API
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=/api/v1
RUN npm run build

FROM python:3.11-slim-bookworm AS python-deps
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-backend-minimal.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements-backend-minimal.txt \
    && pip install email-validator "tensorflow-cpu==2.15.1"

FROM python:3.11-slim-bookworm
WORKDIR /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SMARTRIVER_DEFER_FORECAST=true
ENV SMARTRIVER_SQLITE_PATH=/tmp/smartriver.sqlite3

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

COPY backend/ backend/
COPY data_preprocessing/ data_preprocessing/
COPY ml_engine/ ml_engine/
COPY ml_models/ ml_models/
COPY datasets/ datasets/
COPY modules/ modules/
COPY --from=frontend-build /app/frontend/dist frontend/dist

RUN mkdir -p /tmp

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
