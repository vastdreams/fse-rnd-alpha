"""Flexible XBRL tag mapping with multiple strategies and fallbacks."""
from typing import Dict, List, Optional, Tuple, Any
from src.logging.logger import get_logger

logger = get_logger(__name__)


class XBRLTagMapper:
    """
    Flexible XBRL tag mapper with multiple mapping strategies.
    
    Supports:
    - Primary tag mapping (standard tags)
    - Alternative tag mapping (variations)
    - Fallback strategies
    - Custom tag configurations
    """
    
    def __init__(self):
        """Initialize tag mapper with default mappings."""
        # Primary tag mappings (most common)
        self.primary_mappings = {
            "revenue": [
                "us-gaap:Revenues",
                "us-gaap:SalesRevenueNet",
                "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            ],
            "cost_of_revenue": [
                "us-gaap:CostOfRevenue",
                "us-gaap:CostOfGoodsAndServicesSold",
            ],
            "gross_profit": [
                "us-gaap:GrossProfit",
                "us-gaap:ProfitGross",
            ],
            "rd_expense": [
                "us-gaap:ResearchAndDevelopmentExpense",
                "us-gaap:ResearchDevelopmentAndRelatedExpenses",
            ],
            "operating_income": [
                "us-gaap:OperatingIncomeLoss",
                "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            ],
            "net_income": [
                "us-gaap:NetIncomeLoss",
                "us-gaap:ProfitLoss",
            ],
            "total_assets": [
                "us-gaap:Assets",
            ],
            "total_liabilities": [
                "us-gaap:Liabilities",
            ],
            "total_equity": [
                "us-gaap:Equity",
                "us-gaap:StockholdersEquity",
            ],
            "cash_from_operations": [
                "us-gaap:NetCashProvidedByUsedInOperatingActivities",
                "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            ],
        }
        
        # Alternative tag patterns (for variations)
        self.alternative_patterns = {
            "revenue": [
                r".*Revenue.*",
                r".*Sales.*",
            ],
            "rd_expense": [
                r".*Research.*Development.*",
                r".*R&D.*",
            ],
        }
        
        # Custom mappings (can be loaded from config)
        self.custom_mappings = {}
    
    def add_custom_mapping(self, field_name: str, tags: List[str], priority: int = 0):
        """
        Add custom tag mapping.
        
        Args:
            field_name: Field name (e.g., "revenue")
            tags: List of XBRL tags to try
            priority: Priority level (higher = tried first)
        """
        if field_name not in self.custom_mappings:
            self.custom_mappings[field_name] = []
        
        self.custom_mappings[field_name].append({
            "tags": tags,
            "priority": priority,
        })
    
    def find_tags_for_field(self, field_name: str) -> List[str]:
        """
        Find all possible XBRL tags for a field.
        
        Args:
            field_name: Field name to find tags for
            
        Returns:
            List of XBRL tags in priority order
        """
        tags = []
        
        # Add custom mappings first (highest priority)
        if field_name in self.custom_mappings:
            for mapping in sorted(
                self.custom_mappings[field_name],
                key=lambda x: x["priority"],
                reverse=True
            ):
                tags.extend(mapping["tags"])
        
        # Add primary mappings
        if field_name in self.primary_mappings:
            tags.extend(self.primary_mappings[field_name])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags
    
    def extract_value_with_fallbacks(
        self,
        company_facts: Dict,
        field_name: str,
        fiscal_year: int,
        prefer_annual: bool = True
    ) -> Optional[float]:
        """
        Extract value for a field using all available tag mappings.
        
        Args:
            company_facts: CompanyFacts JSON data
            field_name: Field name to extract
            fiscal_year: Fiscal year
            prefer_annual: Prefer annual over quarterly data
            
        Returns:
            Extracted value or None if not found
        """
        tags = self.find_tags_for_field(field_name)
        
        if not tags:
            logger.warning(f"No tag mappings found for field: {field_name}")
            return None
        
        facts = company_facts.get("facts", {})
        
        # Try each tag in priority order
        for tag in tags:
            value = self._extract_value_for_tag(
                facts,
                tag,
                fiscal_year,
                prefer_annual
            )
            
            if value is not None:
                logger.debug(f"Found value for {field_name} using tag {tag}")
                return value
        
        logger.debug(f"Could not find value for {field_name} with any tag mapping")
        return None
    
    def _extract_value_for_tag(
        self,
        facts: Dict,
        tag: str,
        fiscal_year: int,
        prefer_annual: bool = True
    ) -> Optional[float]:
        """
        Extract value for a specific tag.
        
        Args:
            facts: Facts section from CompanyFacts
            tag: XBRL tag to extract
            fiscal_year: Fiscal year
            prefer_annual: Prefer annual data
            
        Returns:
            Value or None
        """
        # Try each taxonomy
        for taxonomy in ["us-gaap", "dei"]:
            if taxonomy not in facts:
                continue
            
            taxonomy_facts = facts[taxonomy]
            
            # Try exact tag match
            if tag in taxonomy_facts:
                tag_data = taxonomy_facts[tag]
                value = self._extract_value_from_tag_data(
                    tag_data,
                    fiscal_year,
                    prefer_annual
                )
                if value is not None:
                    return value
            
            # Try pattern matching for alternative tags
            import re
            for existing_tag in taxonomy_facts.keys():
                if self._tag_matches_pattern(tag, existing_tag):
                    tag_data = taxonomy_facts[existing_tag]
                    value = self._extract_value_from_tag_data(
                        tag_data,
                        fiscal_year,
                        prefer_annual
                    )
                    if value is not None:
                        logger.debug(f"Found alternative tag match: {existing_tag} for {tag}")
                        return value
        
        return None
    
    def _tag_matches_pattern(self, pattern: str, tag: str) -> bool:
        """Check if tag matches a pattern."""
        import re
        try:
            return bool(re.match(pattern, tag, re.IGNORECASE))
        except Exception:
            return False
    
    def _extract_value_from_tag_data(
        self,
        tag_data: Dict,
        fiscal_year: int,
        prefer_annual: bool
    ) -> Optional[float]:
        """Extract value from tag data for specific fiscal year."""
        from src.utils.date_utils import parse_date, calculate_fiscal_year
        
        units = tag_data.get("units", {})
        
        # Prefer USD, then other units
        unit_keys = ["USD", "USD/shares", "shares"]
        
        for unit_key in unit_keys:
            if unit_key not in units:
                continue
            
            facts = units[unit_key]
            
            # Filter by fiscal year
            annual_facts = []
            quarterly_facts = []
            
            for fact in facts:
                end_date = fact.get("end", "")
                if not end_date:
                    continue
                
                # Skip quarterly if preferring annual
                if prefer_annual and "Q" in end_date.upper():
                    quarterly_facts.append(fact)
                    continue
                
                # Parse date and check fiscal year
                parsed_date = parse_date(end_date)
                if parsed_date:
                    fact_fiscal_year = calculate_fiscal_year(end_date)
                    if fact_fiscal_year == fiscal_year:
                        if "Q" not in end_date.upper():
                            annual_facts.append(fact)
                        else:
                            quarterly_facts.append(fact)
                else:
                    # Fallback: string matching
                    if str(fiscal_year) in end_date and "Q" not in end_date.upper():
                        annual_facts.append(fact)
            
            # Prefer annual facts
            facts_to_use = annual_facts if annual_facts else (quarterly_facts if not prefer_annual else [])
            
            if facts_to_use:
                # Use the most recent fact
                fact = facts_to_use[-1]
                value = fact.get("val")
                if value is not None:
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert value to float: {value}")
        
        return None


# Global mapper instance
_default_mapper = XBRLTagMapper()


def get_tag_mapper() -> XBRLTagMapper:
    """Get default tag mapper instance."""
    return _default_mapper

