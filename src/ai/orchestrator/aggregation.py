"""Aggregate chunk-level signals to company-year factors."""
from typing import List
from src.ai.schemas.rd_chunk_schema import RDChunkSignals
from src.ai.schemas.rd_company_schema import RNDCompanyYearFactors, KeyParagraph
from src.logging.logger import get_logger

logger = get_logger(__name__)


def aggregate_rd_signals(chunk_signals: List[RDChunkSignals]) -> RNDCompanyYearFactors:
    """Aggregate R&D chunk signals into company-year factors."""
    if not chunk_signals:
        return RNDCompanyYearFactors()
    
    total_mentions = sum(
        chunk.signals.get("rd_mentions", 0) for chunk in chunk_signals
    )
    
    all_sentences = []
    for chunk in chunk_signals:
        sentences = chunk.signals.get("rd_sentences", [])
        all_sentences.extend(sentences)
    
    # Aggregate topics
    topic_counts = {}
    for chunk in chunk_signals:
        topics = chunk.signals.get("topics", [])
        for topic in topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    # Get top topics
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    top_topics = [topic for topic, count in sorted_topics[:10]]
    
    # Weighted average tone score
    tone_scores = [
        chunk.signals.get("tone_score", 0.0) for chunk in chunk_signals
        if chunk.signals.get("tone_score") is not None
    ]
    avg_tone = sum(tone_scores) / len(tone_scores) if tone_scores else 0.0
    
    # Estimate word count (rough)
    total_words = sum(
        len(chunk_text.split()) for chunk_text in [
            " ".join(s.get("text", "") for s in chunk.signals.get("rd_sentences", []))
            for chunk in chunk_signals
        ]
    )
    
    # Determine reporting style
    has_numbers = any(
        chunk.signals.get("explicit_numbers") for chunk in chunk_signals
    )
    has_qualitative = total_mentions > 0
    
    if has_numbers and has_qualitative:
        reporting_style = "quantitative_explicit"
    elif has_qualitative:
        reporting_style = "qualitative_only"
    else:
        reporting_style = "boilerplate"
    
    # Select key paragraphs (top 5 by relevance)
    key_paragraphs = []
    for sentence in all_sentences[:10]:  # Top 10 sentences
        if isinstance(sentence, dict):
            key_paragraphs.append(KeyParagraph(
                page=sentence.get("page"),
                text=sentence.get("text", "")[:500],  # Limit length
            ))
    
    return RNDCompanyYearFactors(
        rd_mentions_count=total_mentions,
        rd_section_length_words=total_words,
        rd_tone_score=avg_tone,
        rd_reporting_style=reporting_style,
        rd_focus_tags=top_topics,
        rd_key_paragraphs=key_paragraphs[:5],  # Top 5 paragraphs
    )

