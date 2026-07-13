#!/usr/bin/env bash
# PATH: scripts/verify_finance_gates.sh
# PURPOSE: Local mirror of finance-safe CI gates (formulas, decisions, invariants).
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "== formula registry =="
python3 scripts/audit_formula_registry.py

echo "== decision chains =="
python3 scripts/audit_decision_chains.py

echo "== coverage thresholds self-test =="
python3 scripts/check_coverage_thresholds.py --self-test

echo "== golden rank audit =="
DEBUG=true RANK_INVARIANT_FAIL_CLOSED=1 SECRET_KEY=test-secret-key-for-ci-gates-at-least-32-characters \
  python3 - <<'PY'
import importlib.util
import json
from pathlib import Path

path = Path("backend/app/services/rank_row_invariants.py")
spec = importlib.util.spec_from_file_location("rank_row_invariants", path)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
rows = json.loads(Path("frontend/src/fixtures/rank-golden.json").read_text())["rows"]
mod.assert_rank_rows_invariants(rows)
print("golden_audit_ok", len(rows))
PY

echo "== backend formula/decision/stance tests =="
DEBUG=true SECRET_KEY=test-secret-key-for-ci-gates-at-least-32-characters \
  python3 -m pytest backend/tests/test_formula_math.py backend/tests/test_decision_chains.py backend/tests/test_sell_ceiling.py backend/tests/test_recipe_engine_parity.py backend/tests/test_stance_scores.py backend/tests/test_rank_golden_audit.py -q --tb=line

echo "== frontend invariants =="
(cd frontend && npm run test:invariants && npm run typecheck)

echo "verify_finance_gates: OK"
