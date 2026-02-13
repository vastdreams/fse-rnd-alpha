"""
PATH: backend/app/core/formulas/validation.py
PURPOSE: Validation, documentation, and logging functions for formula outputs
WHY: Separates I→O utility functions from pure data (registry) and schema (spec)
FLOW:
  ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────┐
  │ formula + value  │ →  │ validate/log    │ →  │ (bool, error)    │
  └──────────────────┘    └─────────────────┘    └──────────────────┘
DEPENDENCIES:
  - registry.py: FORMULA_REGISTRY for lookup
"""

import math
import logging
from typing import Dict, Tuple, Optional, Any

from app.core.formulas.registry import FORMULA_REGISTRY

logger = logging.getLogger(__name__)


# ==============================================================================
# Validation Functions
# ==============================================================================

def validate_formula_output(
    formula_name: str, 
    value: float,
    log_warning: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a formula output is within expected range.
    
    Args:
        formula_name: Key in FORMULA_REGISTRY
        value: Computed output value
        log_warning: Whether to log warnings for out-of-range values
        
    Returns:
        (is_valid, error_message)
    """
    if formula_name not in FORMULA_REGISTRY:
        return False, f"Unknown formula: {formula_name}"
    
    spec = FORMULA_REGISTRY[formula_name]
    min_val, max_val = spec.valid_range
    
    if math.isnan(value) or math.isinf(value):
        msg = f"{formula_name} produced invalid value: {value}"
        if log_warning:
            logger.warning(msg)
        return False, msg
    
    if min_val is not None and value < min_val:
        msg = f"{formula_name} value {value} below minimum {min_val}"
        if log_warning:
            logger.warning(msg)
        return False, msg
    
    if max_val is not None and value > max_val:
        msg = f"{formula_name} value {value} above maximum {max_val}"
        if log_warning:
            logger.warning(msg)
        return False, msg
    
    return True, None


def get_formula_documentation(formula_name: str) -> Optional[Dict[str, Any]]:
    """
    Get complete documentation for a formula.
    
    Returns dict with all formula metadata for API/UI display.
    """
    if formula_name not in FORMULA_REGISTRY:
        return None
    
    spec = FORMULA_REGISTRY[formula_name]
    return {
        "name": spec.name,
        "latex": spec.latex,
        "description": spec.description,
        "inputs": spec.inputs,
        "output": spec.output,
        "derivation_steps": spec.derivation_steps,
        "paper_reference": spec.paper_reference,
        "valid_range": {
            "min": spec.valid_range[0],
            "max": spec.valid_range[1],
        },
        "unit": spec.unit,
        "notes": spec.notes,
    }


def get_all_formulas() -> Dict[str, Dict]:
    """
    Get all formulas in a JSON-serializable format.
    
    Used for API documentation and methodology export.
    """
    result = {}
    
    for name, spec in FORMULA_REGISTRY.items():
        result[name] = {
            "name": spec.name,
            "latex": spec.latex,
            "description": spec.description,
            "inputs": spec.inputs,
            "output": spec.output,
            "derivation_steps": spec.derivation_steps,
            "paper_reference": spec.paper_reference,
            "valid_range": {
                "min": spec.valid_range[0],
                "max": spec.valid_range[1],
            },
            "unit": spec.unit,
            "notes": spec.notes,
        }
    
    return result


def log_formula_execution(
    formula_name: str,
    inputs: Dict[str, Any],
    output: float,
    duration_ms: float = 0.0,
    component: str = "unknown"
) -> None:
    """
    Log formula execution for audit trail.
    
    Creates structured log entry that can be parsed for analysis.
    """
    is_valid, error = validate_formula_output(formula_name, output, log_warning=False)
    
    logger.info(
        "Formula executed",
        extra={
            "event_type": "formula_execution",
            "component": component,
            "formula": formula_name,
            "inputs": inputs,
            "output": output,
            "output_valid": is_valid,
            "validation_error": error,
            "duration_ms": duration_ms,
        }
    )


def get_formula(name: str) -> Dict:
    """
    Get a single formula specification.
    
    Args:
        name: Formula name from FORMULA_REGISTRY
        
    Returns:
        Dict with formula details or empty dict if not found
    """
    all_formulas = get_all_formulas()
    return all_formulas.get(name, {})
