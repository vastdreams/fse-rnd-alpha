"""Extract R&D data from financial statements (P/L, Balance Sheet) using GPT vision/structured extraction."""
import json
import re
from typing import Dict, List, Optional
from pathlib import Path
from src.ai.client import call_gpt
from src.logging.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert financial analyst using GPT-5.1 to extract R&D (Research and Development) data from financial statements in SEC 10-K annual reports.

Your task is to READ and UNDERSTAND financial statement tables (not just pattern match) and extract R&D-related line items from:
1. Income Statement (P&L) - Look for R&D expense line items
2. Balance Sheet - Look for R&D-related assets, investments, or capitalized R&D
3. Cash Flow Statement - Look for R&D-related cash flows
4. Notes to Financial Statements - Look for R&D disclosures, accounting policies, breakdowns

R&D can appear in various forms - you must UNDERSTAND the context:
- "Research and Development" expense
- "R&D" expense  
- "Research and development costs"
- "Product development costs" (if clearly R&D-related)
- "Technology development" (if clearly R&D-related)
- "Research" (when in financial context, not general research)
- "Development" (when in R&D context)
- R&D-related assets or investments on balance sheet
- R&D-related cash flows
- Capitalized R&D costs

CRITICAL INSTRUCTIONS:
- READ the table structure - understand rows, columns, headers
- Extract ACTUAL NUMBERS from tables, not narrative text
- Identify the line item name EXACTLY as it appears in the statement
- Extract values for current year and prior years if shown in the table
- Note the currency (USD, etc.) and units (millions, billions, thousands, actual)
- Identify which financial statement it appears in (Income Statement, Balance Sheet, Cash Flow)
- Extract any footnotes or note references
- Handle different table formats (some have years as columns, some as rows)
- Convert units properly (if table says "in millions", multiply by 1,000,000)

DO NOT use fixed pattern matching - READ and UNDERSTAND the financial statements like a human analyst would.

Return structured JSON with all R&D-related financial data found."""


def extract_rd_from_financial_statements(
    html_content: str,
    file_path: Optional[Path] = None,
) -> Dict:
    """Extract R&D data from financial statements in HTML annual report."""
    
    # Step 1: Identify financial statement sections
    # Look for common financial statement patterns
    financial_statement_patterns = [
        r"(?:CONSOLIDATED\s+)?(?:STATEMENTS?\s+OF\s+)?(?:INCOME|OPERATIONS|EARNINGS)",
        r"(?:CONSOLIDATED\s+)?(?:BALANCE\s+)?SHEETS?",
        r"(?:CONSOLIDATED\s+)?(?:STATEMENTS?\s+OF\s+)?(?:CASH\s+FLOWS?)",
        r"NOTES?\s+TO\s+(?:CONSOLIDATED\s+)?(?:FINANCIAL\s+)?STATEMENTS?",
    ]
    
    # Extract financial statement sections
    financial_sections = []
    for pattern in financial_statement_patterns:
        matches = re.finditer(pattern, html_content, re.IGNORECASE)
        for match in matches:
            # Extract context around match (500 chars before and after)
            start = max(0, match.start() - 500)
            end = min(len(html_content), match.end() + 2000)
            financial_sections.append({
                "type": match.group(0),
                "content": html_content[start:end],
            })
    
    if not financial_sections:
        logger.warning("No financial statement sections found in HTML")
        return {}
    
    # Step 2: Use GPT to extract R&D data from financial statements
    user_prompt = f"""Analyze the following financial statement sections from a SEC 10-K annual report and extract ALL R&D-related financial data.

Extract:
1. R&D expense/line items from Income Statement (P&L)
2. R&D-related assets or investments from Balance Sheet
3. R&D-related cash flows
4. R&D disclosures from Notes to Financial Statements

For each R&D item found, extract:
- Line item name (exactly as it appears)
- Current year value
- Prior year value (if shown)
- Currency and units (USD, millions, thousands, etc.)
- Which statement it appears in
- Any footnotes or additional context

FINANCIAL STATEMENT SECTIONS:
{json.dumps([{"type": s["type"], "content": s["content"][:3000]} for s in financial_sections[:5]], indent=2)}

Return JSON in this format:
{{
    "income_statement_rd": [
        {{
            "line_item": "Research and Development",
            "current_year": 2500000000,
            "prior_year": 2300000000,
            "currency": "USD",
            "units": "actual",
            "footnote": "Note 5"
        }}
    ],
    "balance_sheet_rd": [],
    "cash_flow_rd": [],
    "notes_rd": [
        {{
            "note_number": "Note 5",
            "title": "Research and Development",
            "content_summary": "...",
            "key_data": {{}}
        }}
    ],
    "rd_expense_total": 2500000000,
    "rd_as_percent_of_revenue": 15.5,
    "extraction_confidence": 0.95
}}
"""
    
    logger.info("Extracting R&D data from financial statements using GPT")
    response = call_gpt(user_prompt, system_prompt=SYSTEM_PROMPT)
    
    if not response:
        logger.warning("No response from GPT for financial statement extraction")
        return {}
    
    try:
        # Extract JSON from response
        json_str = extract_json_from_response(response)
        if not json_str:
            logger.error("Could not extract JSON from financial statement extraction response")
            return {}
        
        # Validate JSON structure with Pydantic schema
        try:
            from src.ai.schemas.rd_extraction_schema import validate_extracted_json
            validated_result = validate_extracted_json(json_str)
            
            if validated_result:
                # Convert validated result back to dict for compatibility
                data = validated_result.dict(exclude_none=True)
                logger.info(f"Extracted and validated R&D financial data: {len(data.get('income_statement_rd', []))} income statement items")
                return data
            else:
                # Validation failed, but try to use data anyway (partial extraction)
                logger.warning("R&D extraction validation failed, attempting to use unvalidated data")
                data = json.loads(json_str)
                logger.info(f"Extracted R&D financial data (unvalidated): {len(data.get('income_statement_rd', []))} income statement items")
                return data
        except ImportError:
            # Schema module not available, use basic validation
            logger.warning("R&D extraction schema not available, using basic JSON parsing")
            data = json.loads(json_str)
            logger.info(f"Extracted R&D financial data: {len(data.get('income_statement_rd', []))} income statement items")
            return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in financial statement extraction response: {e}")
        logger.debug(f"Response preview: {response[:500]}")
        return {}
    except Exception as e:
        logger.error(f"Error parsing financial statement extraction: {e}", exc_info=True)
        logger.debug(f"Response preview: {response[:500]}")
        return {}


def extract_json_from_response(response: str) -> Optional[str]:
    """Extract JSON from GPT response."""
    # Try to find JSON in code blocks
    if "```json" in response:
        json_str = response.split("```json")[1].split("```")[0].strip()
        return json_str
    elif "```" in response:
        parts = response.split("```")
        if len(parts) >= 3:
            json_str = parts[1].strip()
            if json_str.startswith("json"):
                json_str = json_str[4:].strip()
            return json_str
    
    # Try to find JSON object directly
    brace_start = response.find("{")
    if brace_start != -1:
        brace_count = 0
        for i in range(brace_start, len(response)):
            if response[i] == "{":
                brace_count += 1
            elif response[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    return response[brace_start:i+1]
    
    # Last resort
    response_stripped = response.strip()
    if response_stripped.startswith("{") and response_stripped.endswith("}"):
        return response_stripped
    
    return None


def extract_rd_from_html_tables(html_content: str) -> List[Dict]:
    """
    Extract R&D data by parsing HTML tables directly.
    
    Uses robust table extractor with multiple fallback strategies.
    """
    try:
        # Try robust extractor first
        from src.ai.utils.html_table_extractor import extract_rd_from_html_tables_robust
        rd_data = extract_rd_from_html_tables_robust(html_content)
        
        if rd_data:
            logger.info(f"Extracted {len(rd_data)} R&D items using robust extractor")
            return rd_data
    except ImportError:
        logger.debug("Robust table extractor not available, using fallback")
    except Exception as e:
        logger.warning(f"Robust extractor failed: {e}, trying fallback")
    
    # Fallback to original implementation
    from bs4 import BeautifulSoup
    
    rd_data = []
    
    try:
        soup = BeautifulSoup(html_content, "lxml")
        
        # Find all tables
        tables = soup.find_all("table")
        
        for table in tables:
            # Look for R&D-related headers or cells
            table_text = table.get_text().lower()
            
            rd_keywords = [
                "research and development",
                "r&d",
                "r and d",
                "research",
                "development",
                "product development",
                "technology development",
            ]
            
            has_rd = any(keyword in table_text for keyword in rd_keywords)
            
            if has_rd:
                # Try to extract structured data from table
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        cell_text = " ".join(c.get_text(strip=True) for c in cells)
                        if any(keyword in cell_text.lower() for keyword in rd_keywords):
                            # Extract numbers from cells
                            numbers = []
                            for cell in cells:
                                text = cell.get_text(strip=True)
                                # Try to extract numbers (handle currency, commas, etc.)
                                number_match = re.search(r"[\$]?[\s]*([\d,]+\.?\d*)\s*(?:million|billion|thousand|M|B|K)?", text, re.IGNORECASE)
                                if number_match:
                                    numbers.append({
                                        "text": text,
                                        "value": number_match.group(1).replace(",", ""),
                                    })
                            
                            if numbers:
                                rd_data.append({
                                    "line_item": cell_text,
                                    "values": numbers,
                                    "table_context": table_text[:200],
                                })
        
        logger.info(f"Extracted {len(rd_data)} R&D items from HTML tables (fallback)")
        return rd_data
        
    except Exception as e:
        logger.error(f"Error extracting R&D from HTML tables: {e}")
        return []

