#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] Installing system packages"
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip postgresql-client

echo "[2/5] Creating virtual environment"
python3.11 -m venv .venv
source .venv/bin/activate

echo "[3/5] Installing project dependencies"
python -m pip install --upgrade pip
python -m pip install -e .

echo "[4/5] Installing Playwright browser"
python -m playwright install chromium

echo "[5/5] Bootstrap completed"
echo "Next: configure .env and run SQL scripts in infra/sql"
