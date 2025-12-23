"""Pydantic schemas for R&D extraction validation."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from src.logging.logger import get_logger

logger = get_logger(__name__)


class RDFinancialItem(BaseModel):
    """Schema for R&D financial statement line item."""
    line_item: str = Field(..., description="Line item name as it appears in statement")
    current_year: Optional[float] = Field(None, description="Current year value")
    prior_year: Optional[float] = Field(None, description="Prior year value")
    currency: str = Field(default="USD", description="Currency code")
    units: str = Field(default="actual", description="Units (actual, millions, thousands, etc.)")
    footnote: Optional[str] = Field(None, description="Footnote reference")
    
    @validator('current_year', 'prior_year')
    def validate_amount(cls, v):
        """Validate that amounts are reasonable financial values."""
        if v is None:
            return v
        if abs(v) > 1e15:  # Very large but possible for mega-caps
            logger.warning(f"Very large R&D value detected: {v}")
        return v


class RDNoteItem(BaseModel):
    """Schema for R&D note disclosure."""
    note_number: str = Field(..., description="Note number (e.g., 'Note 5')")
    title: str = Field(..., description="Note title")
    content_summary: Optional[str] = Field(None, description="Summary of note content")
    key_data: Dict[str, Any] = Field(default_factory=dict, description="Key data points from note")


class RDExtractionResult(BaseModel):
    """Schema for complete R&D extraction result."""
    income_statement_rd: List[RDFinancialItem] = Field(default_factory=list)
    balance_sheet_rd: List[RDFinancialItem] = Field(default_factory=list)
    cash_flow_rd: List[RDFinancialItem] = Field(default_factory=list)
    notes_rd: List[RDNoteItem] = Field(default_factory=list)
    rd_expense_total: Optional[float] = Field(None, description="Total R&D expense")
    rd_as_percent_of_revenue: Optional[float] = Field(None, description="R&D as percentage of revenue")
    extraction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score 0-1")
    
    @validator('rd_as_percent_of_revenue')
    def validate_percentage(cls, v):
        """Validate percentage is reasonable (0-100%)."""
        if v is None:
            return v
        if v < 0 or v > 100:
            logger.warning(f"R&D percentage out of expected range: {v}%")
        return v
    
    @validator('extraction_confidence')
    def validate_confidence(cls, v):
        """Validate confidence is between 0 and 1."""
        if v is None:
            return v
        if not 0 <= v <= 1:
            logger.warning(f"Confidence value out of range [0,1]: {v}")
            return max(0.0, min(1.0, v))
        return v


def validate_rd_extraction(data: Dict[str, Any]) -> Optional[RDExtractionResult]:
    """
    Validate R&D extraction result against schema.
    
    Args:
        data: Dictionary containing extraction result
        
    Returns:
        Validated RDExtractionResult or None if validation fails
    """
    try:
        result = RDExtractionResult(**data)
        logger.debug(f"R&D extraction validation passed: {len(result.income_statement_rd)} items")
        return result
    except Exception as e:
        logger.error(f"R&D extraction validation failed: {e}")
        logger.debug(f"Invalid data: {data}")
        return None


def validate_extracted_json(json_str: str) -> Optional[RDExtractionResult]:
    """
    Validate extracted JSON string against schema.
    
    Args:
        json_str: JSON string to validate
        
    Returns:
        Validated RDExtractionResult or None if validation fails
    """
    import json
    
    try:
        data = json.loads(json_str)
        return validate_rd_extraction(data)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        return None
    except Exception as e:
        logger.error(f"Error validating extracted JSON: {e}")
        return None

