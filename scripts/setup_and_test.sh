#!/bin/bash
echo "==============================================="
echo "  ROV Controller - Setup and Test (Linux)"
echo "==============================================="

# switch to repo root (this .sh resides in scripts/)
cd "$(dirname "$0")/.."

echo "Using Python: $PYTHON"
if ! command -v python &> /dev/null; then
  echo "[ERROR] Python not found in PATH."
  echo "Please install Python 3.8+ and ensure 'python' is available."
  exit 2
fi

python scripts/setup_and_test.py
EXITCODE=$?
echo
echo "Done. Exit code: $EXITCODE"
exit $EXITCODE
