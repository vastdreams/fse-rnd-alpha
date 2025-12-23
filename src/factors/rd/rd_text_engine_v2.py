"""Enhanced R&D text engine V2 - orchestrate comprehensive AI R&D text signal extraction."""
import time
from pathlib import Path
from typing import Optional
from src.db.connection import db_session_scope
from src.models.orm.annual_report import AnnualReport
from src.models.orm.text_chunk import TextChunk
from src.models.orm.text_factor_rd import TextFactorRD
from src.models.orm.company_year_core import CompanyYearCore
from src.models.orm.financials_core import FinancialsCore
from src.ingestion.annual_report_text_extractor import extract_report_text
from src.ai.agents.rd_factor_agent_v2 import extract_rd_from_chunk_v2
from src.ai.agents.financial_statement_rd_extractor import (
    extract_rd_from_financial_statements,
    extract_rd_from_html_tables,
)
from src.ai.orchestrator.aggregation_v2 import aggregate_rd_signals_v2
from src.ai.schemas.rd_extraction_v2_schema import RDChunkSignalsV2
from src.logging.logger import get_logger

logger = get_logger(__name__)


def _detach_text_factor(text_factor, session):
    """
    Detach ORM instance safely so callers can read attributes after session closes.
    
    Access fields to ensure they are loaded, then expunge from the session to avoid
    lazy refresh errors once the context manager exits.
    """
    if text_factor is None:
        return None
    _ = (
        text_factor.rd_mentions_count,
        text_factor.research_mentions_count,
        text_factor.development_mentions_count,
        text_factor.innovation_mentions_count,
        text_factor.rd_section_length_words,
        text_factor.extraction_confidence,
        text_factor.extraction_version,
    )
    try:
        session.expunge(text_factor)
    except Exception:
        pass
    return text_factor


def extract_rd_text_factors_v2(company_year_id: int) -> Optional[TextFactorRD]:
    """Extract comprehensive R&D text factors from annual report using V2 extraction."""
    with db_session_scope() as session:
        company_year = session.query(CompanyYearCore).filter_by(id=company_year_id).first()
        if not company_year:
            return None
        
        annual_report = company_year.annual_report
        if not annual_report:
            logger.warning(f"No annual report for company_year_id {company_year_id}")
            return None
        
        # Get or create text factor record
        text_factor = session.query(TextFactorRD).filter_by(company_year_id=company_year_id).first()
        if not text_factor:
            text_factor = TextFactorRD(company_year_id=company_year_id)
            session.add(text_factor)
        
        # Check if already extracted with V2
        if text_factor.extraction_version == "rd_text_agent_v2" and text_factor.rd_mentions_count is not None:
            logger.info(f"R&D text factors already extracted (V2) for company_year_id {company_year_id}")
            return _detach_text_factor(text_factor, session)
        
        # Get report file path
        project_root = Path(__file__).parent.parent.parent.parent
        report_file_path = annual_report.file_path if annual_report.file_path else company_year.report_path
        
        if not report_file_path:
            logger.warning(f"No report path found for company_year_id {company_year_id}")
            return None
        
        report_path = project_root / report_file_path if not Path(report_file_path).is_absolute() else Path(report_file_path)
        
        if not report_path.exists():
            logger.warning(f"Report file not found: {report_path}")
            return None
        
        # Step 1: Extract R&D from financial statements using GPT (not fixed pattern matching)
        logger.info(f"Extracting R&D from financial statements (P/L, Balance Sheet) using GPT-5.1")
        financial_rd_data = {}
        try:
            if report_path.suffix.lower() in [".html", ".htm"]:
                with open(report_path, "r", encoding="utf-8", errors="ignore") as f:
                    html_content = f.read()
                
                # Use GPT to intelligently extract R&D from financial statements
                financial_rd_data = extract_rd_from_financial_statements(html_content, report_path)
                
                # Also try direct table parsing as backup
                if not financial_rd_data:
                    table_rd_data = extract_rd_from_html_tables(html_content)
                    if table_rd_data:
                        financial_rd_data = {"table_extracted": table_rd_data}
                
                logger.info(f"Extracted R&D financial data: {len(financial_rd_data.get('income_statement_rd', []))} items")
        except Exception as e:
            logger.warning(f"Error extracting R&D from financial statements: {e}")
        
        # Step 2: Extract text from report with section identification
        logger.info(f"Extracting text from {report_path}")
        text_blocks = extract_report_text(report_path)
        
        if not text_blocks:
            logger.warning(f"No text extracted from {report_path}")
            return None
        
        # Store text chunks in database with section information
        existing_chunks = session.query(TextChunk).filter_by(annual_report_id=annual_report.id).all()
        if not existing_chunks:
            logger.info(f"Storing {len(text_blocks)} text chunks in database")
            for i, block in enumerate(text_blocks):
                text = block.get("text", "")
                page = block.get("page", i + 1)
                section = block.get("section", "unknown")
                section_title = block.get("section_title")
                
                chunk = TextChunk(
                    annual_report_id=annual_report.id,
                    chunk_id=f"chunk-{i+1}",
                    section_id=section,
                    section_title=section_title,
                    page_start=page,
                    page_end=page,
                    text_content=text,
                    token_count=len(text.split()),
                )
                session.add(chunk)
            session.commit()
            logger.info(f"Stored {len(text_blocks)} text chunks")
        else:
            logger.info(f"Using existing {len(existing_chunks)} text chunks")
            text_blocks = [
                {
                    "page": c.page_start or i+1,
                    "section": c.section_id or "unknown",
                    "section_title": c.section_title,
                    "text": c.text_content or ""
                }
                for i, c in enumerate(sorted(existing_chunks, key=lambda x: x.chunk_id))
            ]
        
        # Process chunks with V2 extraction
        chunk_signals = []
        max_chunks = 50  # Increased limit for comprehensive extraction
        
        for i, block in enumerate(text_blocks[:max_chunks]):
            chunk_id = f"chunk-{i+1}"
            page = block.get("page")
            section = block.get("section", "unknown")
            section_title = block.get("section_title")
            text = block.get("text", "")
            
            # Skip very short chunks
            if len(text) < 100:
                continue
            
            # Extract R&D signals from chunk using V2
            logger.info(f"Processing chunk {i+1}/{min(len(text_blocks), max_chunks)} (section: {section})")
            signals = extract_rd_from_chunk_v2(
                chunk_text=text[:4000],  # Increased limit for better context
                chunk_id=chunk_id,
                page=page,
                section=section,
                section_title=section_title,
            )
            
            if signals and signals.rd_mentions > 0:  # Only add if R&D mentions found
                chunk_signals.append(signals)
            
            # Rate limiting
            time.sleep(1)
        
        # Aggregate signals using V2 aggregation
        if chunk_signals:
            aggregated = aggregate_rd_signals_v2(chunk_signals)
            
            # Update text factor record with comprehensive V2 data
            text_factor.rd_mentions_count = aggregated.rd_mentions_count
            text_factor.research_mentions_count = aggregated.research_mentions_count
            text_factor.development_mentions_count = aggregated.development_mentions_count
            text_factor.innovation_mentions_count = aggregated.innovation_mentions_count
            text_factor.rd_section_length_words = aggregated.rd_section_length_words
            text_factor.rd_tone_score = aggregated.rd_tone_score
            text_factor.rd_sentiment_breakdown = aggregated.sentiment_breakdown
            text_factor.rd_reporting_style = aggregated.rd_reporting_style
            text_factor.rd_sections_found = aggregated.rd_sections_found
            text_factor.rd_primary_section = aggregated.rd_primary_section
            text_factor.rd_focus_tags = aggregated.rd_focus_tags
            text_factor.rd_technology_areas = [
                {
                    "name": ta.name,
                    "mentions": ta.mentions,
                    "contexts": ta.context,
                    "pages": ta.pages,
                }
                for ta in aggregated.rd_technology_areas
            ]
            text_factor.rd_numbers_mentioned = [
                {
                    "value": num.value,
                    "unit": num.unit,
                    "context": num.context,
                    "page": num.page,
                    "section": num.section,
                    "year_reference": num.year_reference,
                    "is_comparative": num.is_comparative,
                }
                for num in aggregated.rd_numbers_mentioned
            ]
            text_factor.rd_percentages_mentioned = [
                {
                    "value": pct.value,
                    "unit": pct.unit,
                    "context": pct.context,
                    "page": pct.page,
                    "section": pct.section,
                    "year_reference": pct.year_reference,
                    "is_comparative": pct.is_comparative,
                }
                for pct in aggregated.rd_percentages_mentioned
            ]
            text_factor.rd_trends_mentioned = [
                {
                    "direction": trend.direction,
                    "context": trend.context,
                    "page": trend.page,
                    "section": trend.section,
                    "magnitude": trend.magnitude,
                    "timeframe": trend.timeframe,
                }
                for trend in aggregated.rd_trends_mentioned
            ]
            text_factor.rd_key_paragraphs = [
                {
                    "page": p.page,
                    "section": p.section,
                    "section_title": p.section_title,
                    "text": p.text,
                    "relevance_score": p.relevance_score,
                    "contains_numbers": p.contains_numbers,
                    "contains_strategy": p.contains_strategy,
                    "sentiment": p.sentiment,
                }
                for p in aggregated.rd_key_paragraphs
            ]
            text_factor.rd_strategic_priorities = aggregated.rd_strategic_priorities
            text_factor.rd_competitive_mentions = aggregated.rd_competitive_mentions
            
            # Store financial statement R&D data (from P/L, Balance Sheet) - GPT-extracted, not fixed pattern
            if financial_rd_data and isinstance(financial_rd_data, dict):
                # Update FinancialsCore if R&D expense found in financial statements
                financials = session.query(FinancialsCore).filter_by(company_year_id=company_year_id).first()
                
                # Process income statement R&D items
                if financial_rd_data.get("income_statement_rd") and isinstance(financial_rd_data["income_statement_rd"], list):
                    rd_items = financial_rd_data["income_statement_rd"]
                    if rd_items and len(rd_items) > 0:
                        # Get the most recent/largest R&D expense value
                        rd_expense = None
                        for item in rd_items:
                            if isinstance(item, dict) and item.get("current_year"):
                                value = float(item.get("current_year", 0))
                                # Convert units if needed
                                units = str(item.get("units", "actual")).lower()
                                if "million" in units or units == "m":
                                    value = value * 1_000_000
                                elif "billion" in units or units == "b":
                                    value = value * 1_000_000_000
                                elif "thousand" in units or units == "k":
                                    value = value * 1_000
                                
                                if rd_expense is None or value > rd_expense:
                                    rd_expense = value
                        
                        if rd_expense and rd_expense > 0:
                            if financials:
                                # Update if missing or significantly different
                                if financials.rd_expense is None:
                                    logger.info(f"Setting R&D expense from financial statements (GPT-extracted): ${rd_expense:,.0f}")
                                    financials.rd_expense = rd_expense
                                    financials.source = "gpt_extracted_financial_statement"
                                elif abs(financials.rd_expense - rd_expense) / max(abs(rd_expense), 1) > 0.1:
                                    logger.info(f"Updating R&D expense from financial statements (GPT-extracted): ${rd_expense:,.0f} (was ${financials.rd_expense:,.0f})")
                                    financials.rd_expense = rd_expense
                                    financials.source = "gpt_extracted_financial_statement"
                            else:
                                # Create FinancialsCore record if it doesn't exist
                                financials = FinancialsCore(company_year_id=company_year_id, rd_expense=rd_expense, source="gpt_extracted_financial_statement")
                                session.add(financials)
                                logger.info(f"Created FinancialsCore with R&D expense from financial statements (GPT-extracted): ${rd_expense:,.0f}")
                
                # Store financial statement extraction results in text_factor numbers
                if not text_factor.rd_numbers_mentioned:
                    text_factor.rd_numbers_mentioned = []
                
                # Add financial statement numbers to the list
                for item in financial_rd_data.get("income_statement_rd", []):
                    if isinstance(item, dict) and item.get("current_year"):
                        value = float(item.get("current_year", 0))
                        units = str(item.get("units", "actual")).lower()
                        # Convert to actual value
                        if "million" in units or units == "m":
                            value = value * 1_000_000
                        elif "billion" in units or units == "b":
                            value = value * 1_000_000_000
                        elif "thousand" in units or units == "k":
                            value = value * 1_000
                        
                        text_factor.rd_numbers_mentioned.append({
                            "value": value,
                            "unit": item.get("currency", "USD"),
                            "context": f"Financial Statement (GPT-extracted): {item.get('line_item', 'R&D Expense')}",
                            "page": None,
                            "section": "Income Statement",
                            "year_reference": "current",
                            "is_comparative": item.get("prior_year") is not None,
                            "source": "financial_statement_gpt",
                        })
                
                # Also add balance sheet and cash flow R&D items if found
                for statement_type in ["balance_sheet_rd", "cash_flow_rd"]:
                    for item in financial_rd_data.get(statement_type, []):
                        if isinstance(item, dict) and item.get("current_year"):
                            value = float(item.get("current_year", 0))
                            units = str(item.get("units", "actual")).lower()
                            if "million" in units or units == "m":
                                value = value * 1_000_000
                            elif "billion" in units or units == "b":
                                value = value * 1_000_000_000
                            
                            text_factor.rd_numbers_mentioned.append({
                                "value": value,
                                "unit": item.get("currency", "USD"),
                                "context": f"Financial Statement (GPT-extracted): {item.get('line_item', 'R&D')}",
                                "page": None,
                                "section": statement_type.replace("_rd", "").replace("_", " ").title(),
                                "year_reference": "current",
                                "is_comparative": item.get("prior_year") is not None,
                                "source": "financial_statement_gpt",
                            })
            
            text_factor.extraction_version = "rd_text_agent_v2"
            text_factor.extraction_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            text_factor.extraction_confidence = aggregated.extraction_confidence
            text_factor.verification_status = aggregated.verification_status
            
            session.commit()
            logger.info(
                f"R&D text factors extracted (V2): {aggregated.rd_mentions_count} mentions, "
                f"{len(aggregated.rd_numbers_mentioned)} numbers, "
                f"{len(aggregated.rd_trends_mentioned)} trends, "
                f"confidence: {aggregated.extraction_confidence:.2f}"
            )
            return _detach_text_factor(text_factor, session)
        else:
            logger.warning("No R&D signals extracted from chunks")
            return None

