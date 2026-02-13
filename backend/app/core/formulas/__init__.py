"""
PATH: backend/app/core/formulas/__init__.py
PURPOSE: Re-export all public symbols for backward-compatible import path
WHY: Consumers import from app.core.formulas — this preserves that contract
"""

from app.core.formulas.spec import FormulaSpec
from app.core.formulas.registry import FORMULA_REGISTRY
from app.core.formulas.validation import (
    validate_formula_output,
    get_formula_documentation,
    get_all_formulas,
    log_formula_execution,
    get_formula,
)

__all__ = [
    # Spec
    "FormulaSpec",
    # Registry
    "FORMULA_REGISTRY",
    # Validation & utilities
    "validate_formula_output",
    "get_formula_documentation",
    "get_all_formulas",
    "log_formula_execution",
    "get_formula",
]
