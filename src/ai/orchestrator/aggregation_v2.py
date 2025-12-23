"""Enhanced aggregation of chunk-level signals to company-year factors."""
from typing import List
from src.ai.schemas.rd_extraction_v2_schema import (
    RDChunkSignalsV2,
    RNDCompanyYearFactorsV2,
    RDTechnologyArea,
    RDKeyParagraph,
    RDNumericMention,
    RDTrendMention,
)
from src.logging.logger import get_logger

logger = get_logger(__name__)


def aggregate_rd_signals_v2(chunk_signals: List[RDChunkSignalsV2]) -> RNDCompanyYearFactorsV2:
    """Aggregate enhanced R&D chunk signals into company-year factors."""
    if not chunk_signals:
        return RNDCompanyYearFactorsV2()
    
    # Aggregate mention counts
    total_rd_mentions = sum(chunk.rd_mentions for chunk in chunk_signals)
    total_research_mentions = sum(chunk.research_mentions for chunk in chunk_signals)
    total_development_mentions = sum(chunk.development_mentions for chunk in chunk_signals)
    total_innovation_mentions = sum(chunk.innovation_mentions for chunk in chunk_signals)
    total_r_and_d_mentions = sum(chunk.r_and_d_mentions for chunk in chunk_signals)
    
    # Aggregate all sentences
    all_sentences = []
    for chunk in chunk_signals:
        all_sentences.extend(chunk.rd_sentences)
    
    # Aggregate technology areas
    tech_area_map = {}
    for chunk in chunk_signals:
        for tech_area in chunk.technology_areas:
            if tech_area.name not in tech_area_map:
                tech_area_map[tech_area.name] = {
                    "mentions": 0,
                    "contexts": set(),
                    "pages": set(),
                }
            tech_area_map[tech_area.name]["mentions"] += tech_area.mentions
            tech_area_map[tech_area.name]["contexts"].update(tech_area.context)
            tech_area_map[tech_area.name]["pages"].update(tech_area.pages)
    
    aggregated_tech_areas = [
        RDTechnologyArea(
            name=name,
            mentions=data["mentions"],
            context=list(data["contexts"]),
            pages=list(data["pages"]),
        )
        for name, data in sorted(tech_area_map.items(), key=lambda x: x[1]["mentions"], reverse=True)
    ]
    
    # Aggregate topics (simple list merge, deduplicate)
    all_topics = set()
    for chunk in chunk_signals:
        all_topics.update(chunk.topics)
    
    # Aggregate numeric mentions
    all_numbers = []
    all_percentages = []
    for chunk in chunk_signals:
        all_numbers.extend(chunk.explicit_numbers)
        all_percentages.extend(chunk.percentages)
    
    # Aggregate trends
    all_trends = []
    for chunk in chunk_signals:
        all_trends.extend(chunk.trends)
    
    # Calculate weighted average tone score
    tone_scores = []
    tone_weights = []
    for chunk in chunk_signals:
        if chunk.rd_mentions > 0:
            tone_scores.append(chunk.tone_score)
            tone_weights.append(chunk.rd_mentions)
    
    avg_tone = (
        sum(t * w for t, w in zip(tone_scores, tone_weights)) / sum(tone_weights)
        if tone_weights else 0.0
    )
    
    # Aggregate sentiment breakdown
    sentiment_totals = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
    sentiment_count = 0
    for chunk in chunk_signals:
        if chunk.sentiment_breakdown:
            for key in sentiment_totals:
                sentiment_totals[key] += chunk.sentiment_breakdown.get(key, 0.0)
            sentiment_count += 1
    
    if sentiment_count > 0:
        sentiment_breakdown = {
            k: v / sentiment_count for k, v in sentiment_totals.items()
        }
    else:
        sentiment_breakdown = {}
    
    # Aggregate sections found
    sections_found = set()
    for chunk in chunk_signals:
        if chunk.section_id and chunk.section_id != "unknown":
            sections_found.add(chunk.section_id)
    
    # Determine primary section (most mentions)
    section_mention_counts = {}
    for chunk in chunk_signals:
        if chunk.section_id and chunk.section_id != "unknown":
            section_mention_counts[chunk.section_id] = (
                section_mention_counts.get(chunk.section_id, 0) + chunk.rd_mentions
            )
    
    primary_section = (
        max(section_mention_counts.items(), key=lambda x: x[1])[0]
        if section_mention_counts else None
    )
    
    # Aggregate strategic priorities
    all_strategic_priorities = set()
    for chunk in chunk_signals:
        all_strategic_priorities.update(chunk.strategic_priorities)
    
    # Aggregate competitive mentions
    all_competitive_mentions = []
    for chunk in chunk_signals:
        all_competitive_mentions.extend(chunk.competitive_mentions)
    
    # Select key paragraphs (top 5 by relevance score)
    all_key_paragraphs = []
    for chunk in chunk_signals:
        for sentence in chunk.rd_sentences:
            if isinstance(sentence, dict):
                sentence_text = sentence.get("text", "")
                sentence_page = sentence.get("page")
                relevance = sentence.get("relevance_score", 0.5)  # Default relevance if not provided
                all_key_paragraphs.append({
                    "relevance": relevance,
                    "page": sentence_page or chunk.page,
                    "section": chunk.section_id,
                    "section_title": chunk.section_title,
                    "text": sentence_text[:1000],
                    "contains_numbers": any(
                        num for num in chunk.explicit_numbers
                        if num.page == (sentence_page or chunk.page)
                    ),
                    "contains_strategy": any(
                        priority.lower() in sentence_text.lower()
                        for priority in chunk.strategic_priorities
                    ),
                    "sentiment": "positive" if chunk.tone_score > 0.3 else ("negative" if chunk.tone_score < -0.3 else "neutral"),
                })
    
    # Sort by relevance and take top 5
    all_key_paragraphs.sort(key=lambda x: x.get("relevance", 0.0), reverse=True)
    top_paragraphs = [
        RDKeyParagraph(
            page=p.get("page"),
            section=p.get("section"),
            section_title=p.get("section_title"),
            text=p.get("text", ""),
            relevance_score=p.get("relevance", 0.0),
            contains_numbers=p.get("contains_numbers", False),
            contains_strategy=p.get("contains_strategy", False),
            sentiment=p.get("sentiment", "neutral"),
        )
        for p in all_key_paragraphs[:5]
    ]
    
    # Calculate word count (rough estimate)
    total_words = sum(
        len(" ".join(s.get("text", "") for s in chunk.rd_sentences).split())
        for chunk in chunk_signals
    )
    
    # Determine reporting style
    has_numbers = len(all_numbers) > 0 or len(all_percentages) > 0
    has_qualitative = total_rd_mentions > 0
    
    if has_numbers and has_qualitative:
        reporting_style = "quantitative_explicit"
    elif has_qualitative:
        reporting_style = "qualitative_only"
    else:
        reporting_style = "boilerplate"
    
    # Calculate extraction confidence
    quality_indicators = [
        total_rd_mentions > 0,
        len(all_numbers) > 0,
        len(all_trends) > 0,
        len(aggregated_tech_areas) > 0,
        len(top_paragraphs) > 0,
        avg_tone != 0.0,
    ]
    extraction_confidence = sum(quality_indicators) / len(quality_indicators)
    
    return RNDCompanyYearFactorsV2(
        rd_mentions_count=total_rd_mentions,
        research_mentions_count=total_research_mentions,
        development_mentions_count=total_development_mentions,
        innovation_mentions_count=total_innovation_mentions,
        r_and_d_mentions_count=total_r_and_d_mentions,
        rd_section_length_words=total_words,
        total_rd_paragraphs=len(all_sentences),
        rd_tone_score=avg_tone,
        sentiment_breakdown=sentiment_breakdown,
        rd_reporting_style=reporting_style,
        rd_sections_found=list(sections_found),
        rd_primary_section=primary_section,
        rd_focus_tags=list(all_topics),
        rd_technology_areas=aggregated_tech_areas,
        rd_numbers_mentioned=all_numbers,
        rd_percentages_mentioned=all_percentages,
        rd_trends_mentioned=all_trends,
        rd_key_paragraphs=top_paragraphs,
        rd_strategic_priorities=list(all_strategic_priorities),
        rd_competitive_mentions=all_competitive_mentions,
        extraction_confidence=extraction_confidence,
        verification_status="unverified",
    )

