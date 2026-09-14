#!/bin/bash
# THE contract for this demo. No arguments, no pre-existing state.
# Exits 0 only if the approval gate genuinely blocks and genuinely unblocks.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
"$PY" --version

echo
echo "step 1/3: unit tests (grammar, gate loop, GitHub adapter over real HTTP)"
"$PY" -m unittest discover -s tests -t . -v 2>&1 | tail -5

echo
echo "step 2/3: end-to-end — gate runs as its own process against a real HTTP API"
echo "          (offline mode: the API is a local GitHub-shaped server)"
"$PY" e2e.py

echo
if [ -n "${GATE_LIVE_REPO:-}" ] && [ -n "${GATE_LIVE_ISSUE:-}" ] \
   && [ -n "${GATE_LIVE_APPROVER:-}" ] && [ -n "${GITHUB_TOKEN:-}" ]; then
  echo "step 3/3: live pass against api.github.com"
  echo "          repo=$GATE_LIVE_REPO issue=$GATE_LIVE_ISSUE (read-only, no comments posted)"
  # Expects an issue that already carries an approval. --timeout 0 means one
  # poll: read the thread, decide, exit.
  "$PY" -m src.gate_cli \
    --repo "$GATE_LIVE_REPO" \
    --issue "$GATE_LIVE_ISSUE" \
    --approver "$GATE_LIVE_APPROVER" \
    --opened-at "${GATE_LIVE_SINCE:-2026-01-01T00:00:00Z}" \
    --timeout 0 \
    --no-nudge
  echo "live pass: the gate read a real human decision off a real issue"
else
  echo "step 3/3: SKIPPED — no live credentials, so the offline run above stands"
  echo "          (set GATE_LIVE_REPO, GATE_LIVE_ISSUE, GATE_LIVE_APPROVER and"
  echo "           GITHUB_TOKEN to also verify against api.github.com)"
fi

echo
echo "verify.sh: OK"
