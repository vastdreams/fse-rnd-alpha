"""Enhanced R&D factor extraction agent with comprehensive structured extraction."""
import json
import re
from typing import Dict, Optional, Any
from pathlib import Path
from src.ai.client import call_gpt
from src.ai.schemas.rd_extraction_v2_schema import RDChunkSignalsV2
from src.logging.logger import get_logger

logger = get_logger(__name__)

# Load the comprehensive prompt
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "rd_extraction_v2_prompt.md"
try:
    with open(PROMPT_FILE, "r") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    SYSTEM_PROMPT = """You are an expert financial analyst specializing in extracting Research & Development (R&D) information from SEC 10-K annual reports. Extract ALL R&D-related information including mentions, numbers, trends, technology areas, and strategic context."""


def extract_rd_from_chunk_v2(
    chunk_text: str,
    chunk_id: str,
    page: Optional[int] = None,
    section: Optional[str] = None,
    section_title: Optional[str] = None,
) -> Optional[RDChunkSignalsV2]:
    """Extract comprehensive R&D signals from a single text chunk using multi-step structured extraction."""
    
    # Step 1: Pre-process text to identify R&D context
    rd_keywords = [
        "research and development", "r&d", "r and d", "research", "development",
        "innovation", "technology development", "product development", "rd spending",
        "rd expense", "rd investment", "rd program", "rd project", "rd facility",
        "rd lab", "rd center"
    ]
    
    text_lower = chunk_text.lower()
    has_rd_context = any(keyword in text_lower for keyword in rd_keywords)
    
    if not has_rd_context and len(chunk_text) > 500:
        # Quick check: if no R&D keywords and text is long, likely no R&D content
        logger.debug(f"Chunk {chunk_id} has no R&D keywords, skipping detailed extraction")
        return None
    
    # Step 2: Construct comprehensive user prompt
    user_prompt = f"""Extract comprehensive R&D-related information from this text chunk from a SEC 10-K annual report.

CHUNK METADATA:
- Chunk ID: {chunk_id}
- Page: {page or "unknown"}
- Section: {section or "unknown"}
- Section Title: {section_title or "unknown"}

TEXT CHUNK:
{chunk_text[:4000]}  # Limit to avoid token limits

EXTRACTION REQUIREMENTS:
1. Count ALL R&D mentions (including "Research", "Development", "R&D", "Innovation" in R&D context)
2. Extract ALL numeric values related to R&D (spending, percentages, headcount, etc.)
3. Identify ALL trends (increasing, decreasing, stable, etc.)
4. Extract ALL technology areas and research domains mentioned
5. Analyze sentiment and tone (positive/neutral/negative breakdown)
6. Identify strategic priorities and competitive mentions
7. Select key paragraphs (max 5) with highest R&D relevance
8. Assess quality indicators (quantitative data, qualitative narrative, boilerplate)

OUTPUT FORMAT:
Return valid JSON matching the RDChunkSignalsV2 schema. Include ALL fields, using empty arrays/zero values for missing information.

IMPORTANT:
- Only extract information EXPLICITLY stated in the text
- Do NOT invent or infer data
- If R&D is not mentioned, return zero counts
- Be comprehensive but accurate
"""

    # Step 3: Call GPT with structured prompt
    logger.info(f"Extracting R&D signals from chunk {chunk_id} (page {page})")
    response = call_gpt(user_prompt, system_prompt=SYSTEM_PROMPT)
    
    if not response:
        logger.warning(f"No response from GPT for chunk {chunk_id}")
        return None
    
    # Step 4: Parse and validate response
    try:
        # Extract JSON from response
        json_str = extract_json_from_response(response)
        if not json_str:
            logger.error(f"Could not extract JSON from response for chunk {chunk_id}")
            logger.debug(f"Response: {response[:500]}")
            return None
        
        # Parse JSON
        data = json.loads(json_str)
        
        # Validate and create Pydantic model
        signals = RDChunkSignalsV2(**data)
        
        # Add metadata
        signals.section_id = section
        signals.section_title = section_title
        signals.page = page
        
        logger.debug(f"Extracted {signals.rd_mentions} R&D mentions from chunk {chunk_id}")
        return signals
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for chunk {chunk_id}: {e}")
        logger.debug(f"Response: {response[:500]}")
        return None
    except Exception as e:
        logger.error(f"Error parsing R&D extraction response for chunk {chunk_id}: {e}")
        logger.debug(f"Response: {response[:500]}")
        return None


def extract_json_from_response(response: str) -> Optional[str]:
    """Extract JSON from GPT response, handling various formats."""
    # Try to find JSON in code blocks
    if "```json" in response:
        json_str = response.split("```json")[1].split("```")[0].strip()
        return json_str
    elif "```" in response:
        # Try generic code block
        parts = response.split("```")
        if len(parts) >= 3:
            json_str = parts[1].strip()
            # Remove language identifier if present
            if json_str.startswith("json"):
                json_str = json_str[4:].strip()
            return json_str
    
    # Try to find JSON object directly
    # Look for { ... } pattern
    brace_start = response.find("{")
    if brace_start != -1:
        brace_count = 0
        for i in range(brace_start, len(response)):
            if response[i] == "{":
                brace_count += 1
            elif response[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_str = response[brace_start:i+1]
                    return json_str
    
    # Last resort: return the whole response if it looks like JSON
    response_stripped = response.strip()
    if response_stripped.startswith("{") and response_stripped.endswith("}"):
        return response_stripped
    
    return None


def verify_extraction_quality(signals: RDChunkSignalsV2) -> Dict[str, Any]:
    """Verify the quality and completeness of extracted signals."""
    quality_metrics = {
        "has_mentions": signals.rd_mentions > 0,
        "has_numbers": len(signals.explicit_numbers) > 0,
        "has_trends": len(signals.trends) > 0,
        "has_technology_areas": len(signals.technology_areas) > 0,
        "has_key_paragraphs": len(signals.rd_sentences) > 0,
        "has_sentiment": signals.tone_score != 0.0 or len(signals.sentiment_breakdown) > 0,
    }
    
    # Calculate confidence score
    quality_score = sum(quality_metrics.values()) / len(quality_metrics)
    
    return {
        "quality_metrics": quality_metrics,
        "confidence_score": quality_score,
        "is_comprehensive": quality_score >= 0.6,
    }

