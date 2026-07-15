#!/usr/bin/env python3
"""
PATH: scripts/validate_company_briefs.py
PURPOSE: Validate every authored brief in research/company-briefs/ against the
report contracts (section ids, word budgets, citation completeness) without
touching the database. CI gate: exits non-zero on any violation.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"


def _load(name: str, relpath: str):
    """Load a backend module by path without executing heavy package inits."""
    for pkg in ("app", "app.contracts", "app.services"):
        if pkg not in sys.modules:
            sys.modules[pkg] = types.ModuleType(pkg)
    spec = importlib.util.spec_from_file_location(name, BACKEND / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_contracts = _load("app.contracts.company_reports", "app/contracts/company_reports.py")
_load("app.services.company_report_metrics", "app/services/company_report_metrics.py")
_builder = _load("app.services.company_report_builder", "app/services/company_report_builder.py")

PAGE1_SECTIONS = _contracts.PAGE1_SECTIONS
PAGE2_SECTIONS = _contracts.PAGE2_SECTIONS
SECTION_WORD_BUDGETS = _contracts.SECTION_WORD_BUDGETS
ReportSection = _contracts.ReportSection
SECTION_TITLES = _builder.SECTION_TITLES
AuthoredBrief = _builder.AuthoredBrief

BRIEFS_DIR = Path(__file__).resolve().parents[1] / "research" / "company-briefs"
EXPECTED_SECTIONS = set(PAGE1_SECTIONS) | set(PAGE2_SECTIONS)


def validate_brief(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text())
    ticker = data.get("ticker", path.stem)
    try:
        authored = AuthoredBrief.model_validate(
            {"sections": data.get("sections", {}), "citations": data.get("citations", [])}
        )
    except ValueError as exc:
        return [f"{ticker}: authored payload invalid: {exc}"]

    provided = set(authored.sections)
    missing = EXPECTED_SECTIONS - provided
    unknown = provided - EXPECTED_SECTIONS
    if missing:
        errors.append(f"{ticker}: missing sections {sorted(missing)}")
    if unknown:
        errors.append(f"{ticker}: unknown sections {sorted(unknown)}")

    known_cites = {c.cite_id for c in authored.citations} | {"S1", "S2", "S3", "S4"}
    for sid, section in authored.sections.items():
        if sid not in SECTION_WORD_BUDGETS:
            continue
        try:
            ReportSection(
                section_id=sid,
                title=SECTION_TITLES.get(sid, sid),
                body=section.body,
                cite_ids=section.cite_ids,
            )
        except ValueError as exc:
            errors.append(f"{ticker}/{sid}: {exc}")
        dangling = set(section.cite_ids) - known_cites
        if dangling:
            errors.append(f"{ticker}/{sid}: unknown cite_ids {sorted(dangling)}")
    return errors


def main() -> int:
    briefs = sorted(BRIEFS_DIR.glob("*.json"))
    if not briefs:
        print(f"No briefs found in {BRIEFS_DIR}", file=sys.stderr)
        return 1
    all_errors: list[str] = []
    for path in briefs:
        errs = validate_brief(path)
        status = "OK" if not errs else f"{len(errs)} error(s)"
        print(f"{path.name}: {status}")
        all_errors.extend(errs)
    for err in all_errors:
        print(f"  ERROR {err}", file=sys.stderr)
    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
