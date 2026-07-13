#!/usr/bin/env bash
# PATH: scripts/run_filing_map_batch.sh
# PURPOSE: Batch DeepSeek filing_map on cached filings (quote-substring locators only).
# Does not invent NRR/MoS. Requires DEEPSEEK_API_KEY.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIMIT="${1:-40}"
cd "$ROOT"
if [[ -x backend/.venv/bin/python ]]; then
  PY=backend/.venv/bin/python
else
  PY=python3
fi
exec "$PY" scripts/deepseek_audit.py filing_map --limit "$LIMIT"
