#!/bin/bash
# THE contract for this demo. No arguments, no pre-existing state, no API key.
# Exits 0 only if the broken warehouse is genuinely caught by its own tests and
# the fixed one genuinely answers correctly.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
"$PY" --version

echo
echo "step 1/3: dependencies (dbt-core, dbt-duckdb) into a local venv"
[ -d .venv ] || "$PY" -m venv .venv
./.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt
PY="./.venv/bin/python"
"$PY" -m dbt.cli.main --version 2>&1 | grep -E 'installed|duckdb:' || true

echo
echo "step 2/3: unit tests (report parsing, query safety, the gate)"
"$PY" -m unittest discover -s tests -t . -v 2>&1 | tail -4

echo
echo "step 3/3: end-to-end — dbt builds the warehouse twice, real DuckDB,"
echo "          same question asked of both"
"$PY" e2e.py

echo
echo "verify.sh: OK"
