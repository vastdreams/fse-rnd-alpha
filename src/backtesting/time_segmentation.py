"""Time segmentation analysis for backtests."""
from typing import List, Dict, Tuple
from datetime import datetime
import pandas as pd
from src.logging.logger import get_logger

logger = get_logger(__name__)


def define_time_segments(start_year: int, end_year: int) -> List[Dict]:
    """Define time segments for subperiod analysis."""
    segments = []
    
    # Market regime segments (can be customized)
    segments.append({
        "name": "Pre-COVID",
        "start_year": start_year,
        "end_year": 2019,
        "description": "Pre-pandemic period"
    })
    
    segments.append({
        "name": "COVID Period",
        "start_year": 2020,
        "end_year": 2021,
        "description": "Pandemic period"
    })
    
    segments.append({
        "name": "Post-COVID",
        "start_year": 2022,
        "end_year": end_year,
        "description": "Post-pandemic recovery"
    })
    
    # Filter to valid segments
    valid_segments = [s for s in segments if s["start_year"] <= end_year and s["end_year"] >= start_year]
    
    return valid_segments


def segment_backtest_results(
    results: List[Dict],
    segments: List[Dict]
) -> Dict[str, List[Dict]]:
    """Segment backtest results by time period."""
    segmented = {}
    
    for segment in segments:
        segment_results = [
            r for r in results
            if segment["start_year"] <= r.get("formation_year", 0) <= segment["end_year"]
        ]
        segmented[segment["name"]] = segment_results
    
    return segmented


def calculate_segment_statistics(
    segmented_results: Dict[str, List[Dict]],
    bucket: str = "decile_10"  # Top decile
) -> Dict[str, Dict]:
    """Calculate statistics for each time segment."""
    segment_stats = {}
    
    for segment_name, results in segmented_results.items():
        bucket_results = [r for r in results if r.get("bucket") == bucket]
        
        if not bucket_results:
            continue
        
        returns = [r.get("mean_ret", 0) for r in bucket_results]
        
        if returns:
            segment_stats[segment_name] = {
                "mean_return": sum(returns) / len(returns),
                "std_return": pd.Series(returns).std() if len(returns) > 1 else 0,
                "n_observations": len(returns),
                "min_return": min(returns),
                "max_return": max(returns),
            }
    
    return segment_stats

