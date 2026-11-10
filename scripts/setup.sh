#!/usr/bin/env bash
# Create a virtual environment, install dependencies and run the tests.
# Usage: ./scripts/setup.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: '$PYTHON' not found. Install Python 3.12 or newer." >&2
  exit 1
fi

if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "ERROR: Python 3.12 or newer is required (found: $("$PYTHON" -V))." >&2
  exit 1
fi

echo "==> Creating virtual environment (.venv)"
"$PYTHON" -m venv .venv

echo "==> Installing dependencies"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements-dev.txt

echo "==> Running tests"
.venv/bin/python -m pytest -q

cat <<'MSG'

Setup complete. Next steps:
  source .venv/bin/activate
  uvicorn app.main:app --host 127.0.0.1 --port 8000
Then open http://127.0.0.1:8000/
MSG
