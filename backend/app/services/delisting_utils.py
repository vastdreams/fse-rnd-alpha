"""
PATH: backend/app/services/delisting_utils.py
PURPOSE:
  - Provide canonical helpers for mapping delisting events to analysis periods.
  - Ensure consistent survivorship-bias correction across July-June and calendar-year code paths.
  - Provide date-range helpers for querying delistings in a given return period.
ROLE IN ARCHITECTURE:
  - Research domain utility (bias-correction / period mapping).
MAIN EXPORTS:
  - delisting_key_year(): Map a delist_date to the correct "return year" bucket.
  - bounds_for_return_year(): Get inclusive (start_date, end_date) for a return year.
NON-RESPONSIBILITIES:
  - This file does NOT ingest delisting returns or touch the database.
  - This file does NOT decide delisting return magnitudes (see ingestion scripts/services).
NOTES FOR FUTURE AI:
  - July-June convention: a "return_year" is the July start year of a Jul(Y)-Jun(Y+1) return period.
  - If a delisting happens in Jan-Jun, it belongs to the previous return_year (Y-1).
  - Keep all period mapping logic centralized here to avoid subtle mismatches.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Tuple


def delisting_key_year(delist_date: date_type, *, use_july_june: bool) -> int:
    """
    Map a delisting date to the correct year key used by return series.

    Inputs:
      - delist_date: datetime.date (must be a real date; callers should guard None)
      - use_july_june:
          - True: map to the July-start "return_year" for Jul(Y)-Jun(Y+1)
          - False: map to calendar year

    Outputs:
      - int year key (return_year if use_july_june else delist_date.year)

    Rationale (July-June):
      - Delisting in Aug 2000 belongs to Jul2000-Jun2001 => return_year=2000
      - Delisting in Feb 2001 belongs to Jul2000-Jun2001 => return_year=2000
    """
    if use_july_june:
        # Jan-Jun belongs to prior July-start period
        return delist_date.year if delist_date.month >= 7 else delist_date.year - 1
    return delist_date.year


def bounds_for_return_year(year: int, *, use_july_june: bool) -> Tuple[date_type, date_type]:
    """
    Get inclusive date bounds for a return year bucket.

    Inputs:
      - year:
          - use_july_june=True: the July start year (return_year)
          - use_july_june=False: calendar year
      - use_july_june: toggle between conventions

    Outputs:
      - (start_date, end_date) inclusive

    Examples:
      - bounds_for_return_year(2000, use_july_june=True)  -> [2000-07-01, 2001-06-30]
      - bounds_for_return_year(2000, use_july_june=False) -> [2000-01-01, 2000-12-31]
    """
    if use_july_june:
        return date_type(year, 7, 1), date_type(year + 1, 6, 30)
    return date_type(year, 1, 1), date_type(year, 12, 31)


