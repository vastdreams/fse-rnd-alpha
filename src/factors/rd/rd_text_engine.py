"""R&D text engine - orchestrate AI R&D text signal extraction."""
import time
from pathlib import Path
from typing import List, Optional
from src.db.connection import db_session_scope
from src.models.orm.annual_report import AnnualReport
from src.models.orm.text_chunk import TextChunk
from src.models.orm.text_factor_rd import TextFactorRD
from src.models.orm.company_year_core import CompanyYearCore
from src.ingestion.annual_report_text_extractor import extract_report_text
from src.ai.agents.rd_factor_agent import extract_rd_from_chunk
from src.ai.orchestrator.aggregation import aggregate_rd_signals
from src.ai.schemas.rd_chunk_schema import RDChunkSignals
from src.logging.logger import get_logger

logger = get_logger(__name__)


def extract_rd_text_factors(company_year_id: int) -> Optional[TextFactorRD]:
    """Extract R&D text factors from annual report."""
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
        
        # Check if already extracted
        if text_factor.rd_mentions_count is not None and text_factor.rd_mentions_count > 0:
            logger.info(f"R&D text factors already extracted for company_year_id {company_year_id}")
            return text_factor
        
        # Get report file path - check both annual_report.file_path and company_year.report_path
        project_root = Path(__file__).parent.parent.parent.parent
        report_file_path = annual_report.file_path if annual_report.file_path else company_year.report_path
        
        if not report_file_path:
            logger.warning(f"No report path found for company_year_id {company_year_id}")
            return None
        
        report_path = project_root / report_file_path if not Path(report_file_path).is_absolute() else Path(report_file_path)
        
        if not report_path.exists():
            logger.warning(f"Report file not found: {report_path}")
            return None
        
        # Extract text from report
        logger.info(f"Extracting text from {report_path}")
        text_blocks = extract_report_text(report_path)
        
        if not text_blocks:
            logger.warning(f"No text extracted from {report_path}")
            return None
        
        # Store text chunks in database
        existing_chunks = session.query(TextChunk).filter_by(annual_report_id=annual_report.id).all()
        if not existing_chunks:
            logger.info(f"Storing {len(text_blocks)} text chunks in database")
            for i, block in enumerate(text_blocks):
                text = block.get("text", "")
                page = block.get("page", i + 1)
                chunk = TextChunk(
                    annual_report_id=annual_report.id,
                    chunk_id=f"chunk-{i+1}",
                    section_id=block.get("section", "unknown"),
                    section_title=block.get("section_title"),
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
                {"page": c.page_start or i+1, "section": c.section_id or "unknown", "text": c.text_content or ""}
                for i, c in enumerate(sorted(existing_chunks, key=lambda x: x.chunk_id))
            ]
        
        # Process chunks (limit to avoid too many API calls)
        chunk_signals = []
        max_chunks = 20  # Limit for testing
        
        for i, block in enumerate(text_blocks[:max_chunks]):
            chunk_id = f"chunk-{i+1}"
            page = block.get("page")
            text = block.get("text", "")
            
            # Skip very short chunks
            if len(text) < 100:
                continue
            
            # Extract R&D signals from chunk
            logger.info(f"Processing chunk {i+1}/{min(len(text_blocks), max_chunks)}")
            signals = extract_rd_from_chunk(
                chunk_text=text[:3000],  # Limit text length
                chunk_id=chunk_id,
                page=page,
            )
            
            if signals:
                chunk_signals.append(signals)
            
            # Rate limiting
            time.sleep(1)
        
        # Aggregate signals
        if chunk_signals:
            aggregated = aggregate_rd_signals(chunk_signals)
            
            # Update text factor record
            text_factor.rd_mentions_count = aggregated.rd_mentions_count
            text_factor.rd_section_length_words = aggregated.rd_section_length_words
            text_factor.rd_tone_score = aggregated.rd_tone_score
            text_factor.rd_reporting_style = aggregated.rd_reporting_style
            text_factor.rd_focus_tags = aggregated.rd_focus_tags
            text_factor.rd_key_paragraphs = [
                {"page": p.page, "section": p.section, "text": p.text}
                for p in aggregated.rd_key_paragraphs
            ]
            text_factor.extraction_version = "rd_text_agent_v1"
            text_factor.extraction_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            session.commit()
            logger.info(f"R&D text factors extracted: {aggregated.rd_mentions_count} mentions")
            return text_factor
        else:
            logger.warning("No R&D signals extracted from chunks")
            return None

