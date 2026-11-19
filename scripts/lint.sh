#!/usr/bin/env bash
# ============================================================================
# Bank Management System - Linting & Static Code Analysis
# Fast sanity check (< 1s) to catch syntax bugs, compiler warnings, and
# undefined variables before building or running tests.
# Usage: bash scripts/lint.sh
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== [1/3] Linting C++ Backend (-Wall -Wextra -fsyntax-only) ==="
g++ -std=c++17 -Wall -Wextra -fsyntax-only backend/main.cpp -Ibackend -Ibackend/third_party
echo "  -> C++ syntax and compiler warnings: PASSED"

echo "=== [2/3] Linting Python Test Files (Bytecode Compilation) ==="
python3 -m py_compile tests/integration/*.py
echo "  -> Python bytecode compilation: PASSED"

echo "=== [3/3] Linting Python Code (Critical Flake8 Checks) ==="
if command -v flake8 &>/dev/null; then
  flake8 tests/integration/ --count --select=E9,F63,F7,F82 --show-source --statistics
  echo "  -> Flake8 critical bug check: PASSED"
elif python3 -m flake8 --version &>/dev/null; then
  python3 -m flake8 tests/integration/ --count --select=E9,F63,F7,F82 --show-source --statistics
  echo "  -> Flake8 critical bug check: PASSED"
else
  echo "  -> (flake8 not installed in current environment; skipping flake8 audit)"
fi

echo ""
echo "All linting checks passed successfully!"
