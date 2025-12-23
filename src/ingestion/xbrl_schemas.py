"""Pydantic schemas for XBRL CompanyFacts JSON validation."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from src.logging.logger import get_logger

logger = get_logger(__name__)


class XBRLFact(BaseModel):
    """Schema for a single XBRL fact."""
    val: Optional[Any] = Field(None, description="Fact value")
    end: str = Field(..., description="End date")
    start: Optional[str] = Field(None, description="Start date")
    accn: Optional[str] = Field(None, description="Accession number")
    fy: Optional[int] = Field(None, description="Fiscal year")
    fp: Optional[str] = Field(None, description="Fiscal period (FY, Q1, Q2, etc.)")
    form: Optional[str] = Field(None, description="Form type (10-K, 10-Q, etc.)")
    filed: Optional[str] = Field(None, description="Filing date")
    frame: Optional[str] = Field(None, description="Frame (e.g., CY2023)")


class XBRLTagData(BaseModel):
    """Schema for XBRL tag data."""
    label: Optional[str] = None
    description: Optional[str] = None
    units: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)


class XBRLTaxonomyFacts(BaseModel):
    """Schema for facts within a taxonomy (us-gaap, dei, etc.)."""
    pass  # Dynamic - will contain tag names as keys


class XBRLFactsSection(BaseModel):
    """Schema for facts section of CompanyFacts."""
    us_gaap: Optional[Dict[str, XBRLTagData]] = Field(None, alias="us-gaap")
    dei: Optional[Dict[str, XBRLTagData]] = Field(None, alias="dei")
    
    class Config:
        allow_population_by_field_name = True


class CompanyFactsSchema(BaseModel):
    """Schema for SEC CompanyFacts JSON response."""
    cik: str = Field(..., description="Company CIK")
    entityName: str = Field(..., description="Company name")
    facts: Optional[XBRLFactsSection] = Field(None, description="Financial facts")
    sic: Optional[str] = Field(None, description="Standard Industrial Classification")
    sicDescription: Optional[str] = Field(None, description="SIC description")
    tickers: Optional[List[str]] = Field(None, description="Stock tickers")
    
    @validator('cik')
    def validate_cik(cls, v):
        """Validate CIK format."""
        if not v:
            return v
        # CIK should be numeric
        if not str(v).replace("0", "").isdigit():
            logger.warning(f"Non-numeric CIK: {v}")
        return v
    
    def get_version(self) -> Optional[str]:
        """Get API version if available in response."""
        # SEC API doesn't explicitly version, but we can detect structure
        if self.facts and hasattr(self.facts, 'us_gaap'):
            return "current"
        return None


def validate_company_facts(data: Dict[str, Any]) -> Optional[CompanyFactsSchema]:
    """
    Validate CompanyFacts JSON response against schema.
    
    Args:
        data: CompanyFacts JSON dictionary
        
    Returns:
        Validated CompanyFactsSchema or None if validation fails
    """
    try:
        result = CompanyFactsSchema(**data)
        logger.debug(f"CompanyFacts validation passed for CIK {result.cik}")
        return result
    except Exception as e:
        logger.error(f"CompanyFacts validation failed: {e}")
        logger.debug(f"Validation error details: {str(e)[:200]}")
        # Try partial validation - at least check for required fields
        if "cik" not in data:
            logger.error("CompanyFacts missing required 'cik' field")
            return None
        return None  # Return None on validation failure


def validate_fact_structure(fact: Dict[str, Any]) -> bool:
    """
    Validate structure of a single fact.
    
    Args:
        fact: Fact dictionary
        
    Returns:
        True if valid, False otherwise
    """
    # Required fields
    if "end" not in fact:
        return False
    
    # Optional but should validate if present
    if "val" in fact:
        val = fact["val"]
        # Value should be numeric or null
        if val is not None and not isinstance(val, (int, float, str)):
            logger.warning(f"Fact value has unexpected type: {type(val)}")
            return False
    
    return True

