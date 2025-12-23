"""
PATH: backend/app/core/sectors.py
PURPOSE:
  - GICS-11 sector normalization
  - Maps various sector/industry labels to canonical GICS sectors
  - Ensures consistent sector classification across data sources

ROLE IN ARCHITECTURE:
  - Data normalization layer
  - Used by FMP client, cohort classifier, and analysis services

MAIN EXPORTS:
  - GICS_SECTORS: Canonical 11 GICS sector names
  - SECTOR_MAPPING: Mapping from raw labels to GICS sectors
  - normalize_sector(): Function to normalize sector names

NOTES FOR FUTURE AI:
  - GICS = Global Industry Classification Standard
  - 11 sectors as of current standard (some older data uses 10)
  - Communication Services was added in 2018 (split from Consumer Discretionary)
"""

from typing import Optional


# ==============================================================================
# GICS-11 Sector Definitions
# ==============================================================================

GICS_SECTORS = [
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
]


# ==============================================================================
# Sector Mapping (raw -> GICS)
# ==============================================================================

SECTOR_MAPPING = {
    # Health Care sector
    "Healthcare": "Health Care",
    "Health Care": "Health Care",
    "Biotechnology": "Health Care",
    "Pharmaceuticals": "Health Care",
    "Pharmaceutical": "Health Care",
    "Medical Devices": "Health Care",
    "Medical Equipment": "Health Care",
    "Healthcare Equipment": "Health Care",
    "Healthcare Services": "Health Care",
    "Life Sciences": "Health Care",
    "Drug Manufacturers": "Health Care",
    
    # Information Technology sector
    "Technology": "Information Technology",
    "Information Technology": "Information Technology",
    "Software": "Information Technology",
    "Semiconductors": "Information Technology",
    "Hardware": "Information Technology",
    "IT Services": "Information Technology",
    "Tech Hardware": "Information Technology",
    "Electronic Equipment": "Information Technology",
    "Communications Equipment": "Information Technology",
    
    # Financials sector
    "Financials": "Financials",
    "Financial Services": "Financials",
    "Financial": "Financials",
    "Banks": "Financials",
    "Insurance": "Financials",
    "Asset Management": "Financials",
    "Capital Markets": "Financials",
    "Consumer Finance": "Financials",
    "Diversified Financial Services": "Financials",
    
    # Consumer Discretionary sector
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Cyclical": "Consumer Discretionary",
    "Retail": "Consumer Discretionary",
    "Restaurants": "Consumer Discretionary",
    "Hotels": "Consumer Discretionary",
    "Leisure": "Consumer Discretionary",
    "Auto Manufacturers": "Consumer Discretionary",
    "Automobiles": "Consumer Discretionary",
    "Apparel": "Consumer Discretionary",
    "Homebuilding": "Consumer Discretionary",
    
    # Consumer Staples sector
    "Consumer Staples": "Consumer Staples",
    "Consumer Defensive": "Consumer Staples",
    "Food Products": "Consumer Staples",
    "Beverages": "Consumer Staples",
    "Household Products": "Consumer Staples",
    "Personal Products": "Consumer Staples",
    "Tobacco": "Consumer Staples",
    
    # Communication Services sector
    "Communication Services": "Communication Services",
    "Telecommunications": "Communication Services",
    "Telecom": "Communication Services",
    "Media": "Communication Services",
    "Interactive Media": "Communication Services",
    "Entertainment": "Communication Services",
    
    # Industrials sector
    "Industrials": "Industrials",
    "Industrial Goods": "Industrials",
    "Aerospace": "Industrials",
    "Aerospace & Defense": "Industrials",
    "Defense": "Industrials",
    "Airlines": "Industrials",
    "Machinery": "Industrials",
    "Transportation": "Industrials",
    "Railroads": "Industrials",
    "Building Products": "Industrials",
    "Construction": "Industrials",
    
    # Energy sector
    "Energy": "Energy",
    "Oil & Gas": "Energy",
    "Oil": "Energy",
    "Gas": "Energy",
    "Petroleum": "Energy",
    "Energy Equipment & Services": "Energy",
    
    # Materials sector
    "Materials": "Materials",
    "Basic Materials": "Materials",
    "Chemicals": "Materials",
    "Mining": "Materials",
    "Metals": "Materials",
    "Paper": "Materials",
    "Packaging": "Materials",
    
    # Real Estate sector
    "Real Estate": "Real Estate",
    "REITs": "Real Estate",
    "REIT": "Real Estate",
    "Property": "Real Estate",
    
    # Utilities sector
    "Utilities": "Utilities",
    "Electric Utilities": "Utilities",
    "Gas Utilities": "Utilities",
    "Water Utilities": "Utilities",
}


# ==============================================================================
# Normalization Functions
# ==============================================================================

def normalize_sector(raw_sector: Optional[str]) -> Optional[str]:
    """
    Normalize a sector name to GICS-11 standard.
    
    Args:
        raw_sector: Raw sector name from data source
        
    Returns:
        Canonical GICS sector name, or None if unrecognized
    """
    if raw_sector is None:
        return None
    
    # Clean input
    clean = raw_sector.strip()
    
    # Direct lookup
    if clean in SECTOR_MAPPING:
        return SECTOR_MAPPING[clean]
    
    # Already canonical
    if clean in GICS_SECTORS:
        return clean
    
    # Case-insensitive lookup
    for raw, gics in SECTOR_MAPPING.items():
        if raw.lower() == clean.lower():
            return gics
    
    # Partial matching for common patterns
    clean_lower = clean.lower()
    
    if "health" in clean_lower or "bio" in clean_lower or "pharma" in clean_lower:
        return "Health Care"
    if "tech" in clean_lower or "software" in clean_lower or "semi" in clean_lower:
        return "Information Technology"
    if "financ" in clean_lower or "bank" in clean_lower or "insur" in clean_lower:
        return "Financials"
    if "energy" in clean_lower or "oil" in clean_lower or "gas" in clean_lower:
        return "Energy"
    if "utilit" in clean_lower or "electric" in clean_lower:
        return "Utilities"
    if "real estate" in clean_lower or "reit" in clean_lower:
        return "Real Estate"
    if "industrial" in clean_lower or "aerospace" in clean_lower:
        return "Industrials"
    if "material" in clean_lower or "chemical" in clean_lower:
        return "Materials"
    if "telecom" in clean_lower or "media" in clean_lower or "communication" in clean_lower:
        return "Communication Services"
    if "consumer" in clean_lower and ("staple" in clean_lower or "defensive" in clean_lower):
        return "Consumer Staples"
    if "consumer" in clean_lower or "retail" in clean_lower:
        return "Consumer Discretionary"
    
    # Unknown sector
    return None


def validate_sector(sector: Optional[str]) -> bool:
    """
    Check if a sector is a valid GICS-11 sector.
    
    Args:
        sector: Sector name to validate
        
    Returns:
        True if valid GICS-11 sector, False otherwise
    """
    return sector in GICS_SECTORS

