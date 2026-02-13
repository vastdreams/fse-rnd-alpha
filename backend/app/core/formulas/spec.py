"""
PATH: backend/app/core/formulas/spec.py
PURPOSE: FormulaSpec dataclass — schema for mathematical formula specifications
WHY: Single source of truth for the shape of a formula definition
FLOW:
  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
  │ Formula data │ →  │ FormulaSpec │ →  │ Validation   │
  └──────────────┘    └─────────────┘    └──────────────┘
DEPENDENCIES: None (pure dataclass)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


@dataclass
class FormulaSpec:
    """
    Complete specification for a mathematical formula.
    
    Provides:
    - Human-readable documentation
    - LaTeX representation for papers
    - Validation constraints
    - Derivation chain for audit
    """
    name: str
    latex: str
    description: str
    inputs: Dict[str, str]  # param_name -> description
    output: str
    derivation_steps: List[str]
    paper_reference: str
    valid_range: Tuple[Optional[float], Optional[float]]  # (min, max), None = unbounded
    unit: str = ""
    notes: List[str] = field(default_factory=list)
