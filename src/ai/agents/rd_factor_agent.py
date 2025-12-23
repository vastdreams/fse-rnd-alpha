"""R&D factor extraction agent - extracts R&D signals from text chunks."""
import json
from typing import Dict, Optional
from src.ai.client import call_gpt
from src.ai.schemas.rd_chunk_schema import RDChunkSignals
from src.logging.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an extraction engine for R&D factor analysis.
You will be given a chunk of text from a 10-K annual report filing.
Your job is to extract ONLY R&D-related information that is present in THIS CHUNK.

Rules:
1. If information is NOT present in this chunk, respond with null/empty for that field.
2. Do NOT invent numbers or information.
3. Do NOT aggregate across years or documents.
4. Return valid JSON only matching the schema.

Extract:
- Count of R&D mentions
- R&D-related sentences with page numbers if available
- Topics mentioned (e.g., "AI", "Cloud", "Robotics", "Biotech")
- Tone score (-1 = defensive/cost-cutting, 0 = neutral, +1 = opportunity-focused investment)
- Any explicit R&D numbers mentioned in the text
"""


def extract_rd_from_chunk(
    chunk_text: str,
    chunk_id: str,
    page: Optional[int] = None,
    section: Optional[str] = None,
) -> Optional[RDChunkSignals]:
    """Extract R&D signals from a single text chunk."""
    user_prompt = f"""Extract R&D-related information from this text chunk.

Chunk ID: {chunk_id}
Page: {page or "unknown"}
Section: {section or "unknown"}

Text:
{chunk_text[:3000]}  # Limit to avoid token limits

Return JSON in this format:
{{
    "chunk_id": "{chunk_id}",
    "factor_family": "R&D",
    "signals": {{
        "rd_mentions": <integer count>,
        "rd_sentences": [
            {{"text": "...", "page": {page or None}}}
        ],
        "topics": ["topic1", "topic2"],
        "tone_score": <float between -1 and 1>,
        "explicit_numbers": []
    }}
}}
"""

    response = call_gpt(user_prompt, system_prompt=SYSTEM_PROMPT)
    if not response:
        return None
    
    try:
        # Try to extract JSON from response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
        
        data = json.loads(json_str)
        return RDChunkSignals(**data)
        
    except Exception as e:
        logger.error(f"Error parsing R&D extraction response: {e}")
        logger.debug(f"Response was: {response}")
        return None

