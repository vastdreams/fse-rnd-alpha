"""Robust HTML table extraction for financial statements."""
from typing import List, Dict, Optional, Tuple, Any
from bs4 import BeautifulSoup, Tag
import re
from src.logging.logger import get_logger

logger = get_logger(__name__)


class HTMLTableExtractor:
    """
    Robust HTML table extractor for financial statements.
    
    Handles:
    - Multiple table formats
    - Nested tables
    - Merged cells
    - Various number formats
    - Currency symbols
    """
    
    def __init__(self):
        """Initialize extractor."""
        # Common financial line item patterns
        self.financial_patterns = {
            "rd": [
                r"research\s+and\s+development",
                r"r\s*[&]\s*d",
                r"r\s+and\s+d",
                r"product\s+development",
                r"technology\s+development",
            ],
            "revenue": [
                r"revenue",
                r"sales",
                r"net\s+sales",
            ],
            "income": [
                r"net\s+income",
                r"profit",
                r"earnings",
            ],
        }
        
        # Number extraction patterns
        self.number_patterns = [
            r"[\$]?[\s]*([\d,]+\.?\d*)\s*(?:million|billion|thousand|M|B|K|m|b|k)?",
            r"\(([\d,]+\.?\d*)\)",  # Negative numbers in parentheses
            r"([\d,]+\.?\d*)\s*\$",
        ]
    
    def extract_table(self, html_content: str, context: Optional[str] = None) -> List[Dict]:
        """
        Extract all relevant tables from HTML.
        
        Args:
            html_content: HTML content
            context: Optional context hint (e.g., "rd", "revenue")
            
        Returns:
            List of extracted table data dictionaries
        """
        try:
            # Try multiple parsers for robustness
            soup = self._parse_html(html_content)
            if not soup:
                return []
            
            tables = soup.find_all("table")
            extracted = []
            
            for table_idx, table in enumerate(tables):
                try:
                    table_data = self._extract_table_structure(table, context)
                    if table_data:
                        table_data["table_index"] = table_idx
                        extracted.append(table_data)
                except Exception as e:
                    logger.warning(f"Error extracting table {table_idx}: {e}")
                    continue
            
            logger.info(f"Extracted {len(extracted)} tables from HTML")
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting tables from HTML: {e}")
            return []
    
    def _parse_html(self, html_content: str) -> Optional[BeautifulSoup]:
        """Parse HTML with multiple parser fallbacks."""
        parsers = ["lxml", "html.parser", "html5lib"]
        
        for parser in parsers:
            try:
                soup = BeautifulSoup(html_content, parser)
                if soup:
                    return soup
            except Exception as e:
                logger.debug(f"Parser {parser} failed: {e}")
                continue
        
        logger.error("All HTML parsers failed")
        return None
    
    def _extract_table_structure(self, table: Tag, context: Optional[str] = None) -> Optional[Dict]:
        """
        Extract structured data from a table.
        
        Args:
            table: BeautifulSoup table tag
            context: Optional context hint
            
        Returns:
            Dictionary with table structure and data
        """
        rows = table.find_all("tr")
        if not rows:
            return None
        
        # Detect table orientation (header row, data rows)
        header_row_idx = self._find_header_row(rows)
        
        # Extract headers
        headers = []
        if header_row_idx is not None:
            header_row = rows[header_row_idx]
            headers = self._extract_row_cells(header_row)
        
        # Extract data rows
        data_rows = []
        for row_idx, row in enumerate(rows):
            if row_idx == header_row_idx:
                continue
            
            cells = self._extract_row_cells(row)
            if cells:
                # Match cells with headers if available
                row_data = {}
                for idx, cell in enumerate(cells):
                    header = headers[idx] if idx < len(headers) else f"column_{idx}"
                    row_data[header] = cell
                
                data_rows.append(row_data)
        
        # Check if table is relevant to context
        if context and not self._is_relevant_table(table, context):
            return None
        
        return {
            "headers": headers,
            "rows": data_rows,
            "row_count": len(data_rows),
            "column_count": len(headers) if headers else 0,
        }
    
    def _find_header_row(self, rows: List[Tag]) -> Optional[int]:
        """Find the header row index (usually first row with non-numeric content)."""
        for idx, row in enumerate(rows[:5]):  # Check first 5 rows
            cells = self._extract_row_cells(row)
            if not cells:
                continue
            
            # Header row typically has text labels, not just numbers
            text_count = sum(1 for cell in cells if not self._is_mostly_numeric(cell))
            if text_count >= len(cells) * 0.5:  # At least 50% text
                return idx
        
        return 0  # Default to first row
    
    def _extract_row_cells(self, row: Tag) -> List[str]:
        """Extract cells from a table row, handling merged cells."""
        cells = []
        
        for cell in row.find_all(["td", "th"]):
            # Get cell text
            text = cell.get_text(strip=True)
            
            # Handle rowspan/colspan
            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))
            
            # Add cell text
            cells.append(text)
            
            # Add empty cells for colspan > 1
            for _ in range(colspan - 1):
                cells.append("")
        
        return cells
    
    def _is_mostly_numeric(self, text: str) -> bool:
        """Check if text is mostly numeric."""
        if not text:
            return False
        
        # Remove currency symbols, commas, spaces
        cleaned = re.sub(r"[\$,\s]", "", text)
        if not cleaned:
            return False
        
        # Check if it's mostly digits or negative sign
        numeric_chars = sum(1 for c in cleaned if c.isdigit() or c in "-.")
        return numeric_chars / len(cleaned) > 0.7
    
    def _is_relevant_table(self, table: Tag, context: str) -> bool:
        """Check if table is relevant to given context."""
        table_text = table.get_text().lower()
        
        if context in self.financial_patterns:
            patterns = self.financial_patterns[context]
            for pattern in patterns:
                if re.search(pattern, table_text, re.IGNORECASE):
                    return True
        
        return False
    
    def extract_numbers_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract numbers from text with context.
        
        Args:
            text: Text to extract numbers from
            
        Returns:
            List of number dictionaries with value and context
        """
        numbers = []
        
        for pattern in self.number_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                number_str = match.group(1).replace(",", "")
                try:
                    value = float(number_str)
                    
                    # Check for negative (parentheses or minus)
                    if "(" in match.group(0) or text[max(0, match.start()-1):match.start()] == "-":
                        value = -abs(value)
                    
                    # Check for multiplier (million, billion, etc.)
                    multiplier_text = match.group(0).lower()
                    if "billion" in multiplier_text or "b" in multiplier_text:
                        value *= 1e9
                    elif "million" in multiplier_text or "m" in multiplier_text:
                        value *= 1e6
                    elif "thousand" in multiplier_text or "k" in multiplier_text:
                        value *= 1e3
                    
                    numbers.append({
                        "value": value,
                        "original_text": match.group(0),
                        "context": text[max(0, match.start()-20):match.end()+20],
                    })
                except (ValueError, TypeError):
                    continue
        
        return numbers
    
    def extract_financial_line_items(
        self,
        html_content: str,
        line_item_keywords: List[str]
    ) -> List[Dict]:
        """
        Extract specific financial line items from HTML tables.
        
        Args:
            html_content: HTML content
            line_item_keywords: Keywords to search for (e.g., ["research", "development"])
            
        Returns:
            List of extracted line items with values
        """
        tables = self.extract_table(html_content)
        results = []
        
        keyword_pattern = "|".join(line_item_keywords)
        pattern = re.compile(keyword_pattern, re.IGNORECASE)
        
        for table_data in tables:
            for row in table_data.get("rows", []):
                # Search in all cells
                for header, cell_value in row.items():
                    if isinstance(cell_value, str) and pattern.search(cell_value):
                        # Extract numbers from this row
                        row_text = " ".join(str(v) for v in row.values())
                        numbers = self.extract_numbers_from_text(row_text)
                        
                        if numbers:
                            results.append({
                                "line_item": cell_value,
                                "values": numbers,
                                "table_context": header,
                            })
        
        return results


def extract_rd_from_html_tables_robust(html_content: str) -> List[Dict]:
    """
    Robust extraction of R&D data from HTML tables.
    
    This is an improved version of the existing extract_rd_from_html_tables function.
    """
    extractor = HTMLTableExtractor()
    
    # Extract R&D-related tables
    rd_keywords = [
        "research and development",
        "r&d",
        "r and d",
        "research",
        "development",
        "product development",
        "technology development",
    ]
    
    line_items = extractor.extract_financial_line_items(html_content, rd_keywords)
    
    logger.info(f"Extracted {len(line_items)} R&D line items from HTML tables")
    return line_items

