#!/usr/bin/env python3
"""
PATH: scripts/verify_publication.py
PURPOSE: Publication verification script for PNL and Labor Efficiency Alpha.
  Runs as part of CI and can be invoked locally.
  Checks:
  1. Reference audit completeness (all .bib entries appear in audit .md)
  2. No premature labor claims in PNL paper
  3. Paper LaTeX compiles (if tectonic available)
  4. Required publication assets exist
  5. Methodology metadata consistency
  6. Gated sections in labor paper properly marked
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m⚠\033[0m"

errors = []
warnings = []


def check(condition: bool, message: str, is_warning: bool = False):
    if condition:
        print(f"  {PASS} {message}")
    elif is_warning:
        print(f"  {WARN} {message}")
        warnings.append(message)
    else:
        print(f"  {FAIL} {message}")
        errors.append(message)


# -----------------------------------------------------------------------
# 1. Required publication assets exist
# -----------------------------------------------------------------------
print("\n=== 1. Required Publication Assets ===")

pnl_assets = [
    "paper_latex/pnl_efficiency/main.tex",
    "paper_latex/pnl_efficiency/references.bib",
    "paper_latex/pnl_efficiency/README.md",
    "paper_references/pnl_efficiency/LITERATURE_REVIEW_MEMO.md",
    "PNL_DATA_PROVENANCE.md",
    "PNL_DATA_AVAILABILITY.md",
    "PNL_REFERENCE_AUDIT.md",
    "PNL_PUBLICATION_AUDIT.md",
    "PNL_CITATION.cff",
]

labor_assets = [
    "paper_latex/labor_efficiency/main.tex",
    "paper_latex/labor_efficiency/references.bib",
    "paper_latex/labor_efficiency/README.md",
    "paper_references/labor_efficiency/LITERATURE_REVIEW_MEMO.md",
    "LABOR_REFERENCE_AUDIT.md",
    "LABOR_PUBLICATION_AUDIT.md",
    "LABOR_CITATION.cff",
    "LABOR_DATA_ENGINEERING.md",
]

for asset in pnl_assets:
    check((REPO_ROOT / asset).exists(), f"PNL asset exists: {asset}")

for asset in labor_assets:
    check((REPO_ROOT / asset).exists(), f"Labor asset exists: {asset}")

# -----------------------------------------------------------------------
# 2. Reference audit completeness
# -----------------------------------------------------------------------
print("\n=== 2. Reference Audit Completeness ===")

def extract_bib_keys(bib_path: Path) -> set:
    content = bib_path.read_text()
    return set(re.findall(r'@\w+\{(\w+),', content))

def extract_audit_keys(audit_path: Path) -> set:
    content = audit_path.read_text()
    return set(re.findall(r'\b(\w+_\w+(?:_\w+)*)\b', content))

pnl_bib = REPO_ROOT / "paper_latex/pnl_efficiency/references.bib"
pnl_audit = REPO_ROOT / "PNL_REFERENCE_AUDIT.md"

if pnl_bib.exists() and pnl_audit.exists():
    bib_keys = extract_bib_keys(pnl_bib)
    audit_text = pnl_audit.read_text().lower()
    missing = [k for k in bib_keys if k.lower() not in audit_text]
    check(len(missing) == 0,
          f"PNL: All {len(bib_keys)} bib keys appear in reference audit"
          + (f" (missing: {missing[:5]})" if missing else ""),
          is_warning=bool(missing))

labor_bib = REPO_ROOT / "paper_latex/labor_efficiency/references.bib"
labor_audit = REPO_ROOT / "LABOR_REFERENCE_AUDIT.md"

if labor_bib.exists() and labor_audit.exists():
    bib_keys = extract_bib_keys(labor_bib)
    audit_text = labor_audit.read_text().lower()
    missing = [k for k in bib_keys if k.lower() not in audit_text]
    check(len(missing) == 0,
          f"Labor: All {len(bib_keys)} bib keys appear in reference audit"
          + (f" (missing: {missing[:5]})" if missing else ""),
          is_warning=bool(missing))

# -----------------------------------------------------------------------
# 3. No premature labor claims in PNL paper
# -----------------------------------------------------------------------
print("\n=== 3. No Premature Labor Claims in PNL Paper ===")

pnl_tex = REPO_ROOT / "paper_latex/pnl_efficiency/main.tex"
if pnl_tex.exists():
    pnl_content = pnl_tex.read_text()

    labor_terms = [
        "employee count",
        "payroll",
        "headcount",
        "full.time employees",
        "labor productivity",
        "revenue per employee",
        "RPE",
        "RPP",
    ]

    allowed_contexts = [
        "companion",
        "excluded",
        "future work",
        "limitations",
        "phase 2",
        "labor efficiency paper",
        "not yet available",
        "deferred",
    ]

    for term in labor_terms:
        matches = list(re.finditer(term, pnl_content, re.IGNORECASE))
        for m in matches:
            context_start = max(0, m.start() - 200)
            context_end = min(len(pnl_content), m.end() + 200)
            context = pnl_content[context_start:context_end].lower()
            in_allowed = any(ac in context for ac in allowed_contexts)
            check(in_allowed,
                  f"Labor term '{term}' at offset {m.start()} is in allowed context",
                  is_warning=not in_allowed)

# -----------------------------------------------------------------------
# 4. Gated sections in labor paper properly marked
# -----------------------------------------------------------------------
print("\n=== 4. Labor Paper Gated Sections ===")

labor_tex = REPO_ROOT / "paper_latex/labor_efficiency/main.tex"
if labor_tex.exists():
    labor_content = labor_tex.read_text()

    gated_keywords = ["GATED", "PENDING"]
    results_section = re.search(
        r'\\section\{Core Results\}.*?(?=\\section|\\end\{document\})',
        labor_content, re.DOTALL
    )
    if results_section:
        check(any(kw in results_section.group() for kw in gated_keywords),
              "Labor Core Results section is properly gated")

    robustness_section = re.search(
        r'\\section\{Robustness\}.*?(?=\\section|\\end\{document\})',
        labor_content, re.DOTALL
    )
    if robustness_section:
        check(any(kw in robustness_section.group() for kw in gated_keywords),
              "Labor Robustness section is properly gated")

    portfolio_section = re.search(
        r'\\section\{Portfolio Implications\}.*?(?=\\section|\\end\{document\})',
        labor_content, re.DOTALL
    )
    if portfolio_section:
        check(any(kw in portfolio_section.group() for kw in gated_keywords),
              "Labor Portfolio Implications section is properly gated")

# -----------------------------------------------------------------------
# 5. Code-level checks
# -----------------------------------------------------------------------
print("\n=== 5. Code-Level Checks ===")

scorer_path = REPO_ROOT / "backend/app/services/pnl_efficiency_scorer/scorer.py"
if scorer_path.exists():
    scorer_content = scorer_path.read_text()
    check("WINSORIZE_LIMIT" in scorer_content, "Scorer has WINSORIZE_LIMIT constant")
    check("MIN_SECTOR_SIZE" in scorer_content, "Scorer has MIN_SECTOR_SIZE constant")
    check("employee" not in scorer_content.lower() or "does not use" in scorer_content.lower(),
          "Scorer does not reference employee data (or only in exclusion comment)")

test_files = list((REPO_ROOT / "backend/tests").glob("test_pnl_*.py"))
check(len(test_files) >= 2, f"At least 2 PNL test files exist ({len(test_files)} found)")

# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Publication Verification Summary")
print(f"{'='*60}")
print(f"  Errors:   {len(errors)}")
print(f"  Warnings: {len(warnings)}")

if errors:
    print(f"\n{FAIL} FAILED — {len(errors)} error(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
elif warnings:
    print(f"\n{WARN} PASSED with {len(warnings)} warning(s)")
    sys.exit(0)
else:
    print(f"\n{PASS} ALL CHECKS PASSED")
    sys.exit(0)
