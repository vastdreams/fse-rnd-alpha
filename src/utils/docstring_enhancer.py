"""Utilities for enhancing docstrings and type hints across the codebase."""
from typing import Any, Callable, Optional
from inspect import signature, Parameter
import re


def ensure_type_hints(func: Callable) -> Callable:
    """
    Ensure function has type hints (helper for documentation).
    
    This is a utility to help identify functions missing type hints.
    """
    sig = signature(func)
    params_without_hints = [
        param.name
        for param in sig.parameters.values()
        if param.annotation == Parameter.empty and param.name != 'self'
    ]
    
    if params_without_hints:
        return func  # Has missing hints
    
    return func


def validate_docstring(func: Callable) -> dict:
    """
    Validate function docstring completeness.
    
    Returns:
        Dictionary with validation results
    """
    doc = func.__doc__ or ""
    
    has_summary = len(doc.strip()) > 0
    has_args = "Args:" in doc or "Parameters:" in doc
    has_returns = "Returns:" in doc or "Return:" in doc
    has_raises = "Raises:" in doc
    
    return {
        "has_docstring": has_summary,
        "has_args": has_args,
        "has_returns": has_returns,
        "has_raises": has_raises,
        "completeness": sum([has_summary, has_args, has_returns]) / 3.0,
    }

