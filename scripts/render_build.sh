#!/usr/bin/env bash
set -euo pipefail

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing backend dependencies (minimal first)"
pip install --no-cache-dir -r requirements-backend-minimal.txt
pip install --no-cache-dir email-validator

echo "==> Installing TensorFlow CPU (large — may take several minutes)"
pip install --no-cache-dir "tensorflow-cpu==2.15.1"

echo "==> Building frontend"
cd frontend
npm ci
export VITE_API_URL=/api/v1
npm run build
cd ..

echo "==> Build complete"
