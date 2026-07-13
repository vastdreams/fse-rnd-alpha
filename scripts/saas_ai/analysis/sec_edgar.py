"""
Minimal SEC EDGAR fetch helpers for filing-backed qualitative fields.

The functions return raw filing metadata/text URLs. Deterministic extraction is
performed by separate modules.
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
from typing import Any


USER_AGENT = "Finsoeasy research contact: research@finsoeasy.com"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{document}"
ANNUAL_FORMS = {"10-K", "20-F", "40-F"}
EVENT_FORMS = {"8-K", "6-K"}


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return html.unescape(_strip_tags(raw))


def ticker_cik_map() -> dict[str, str]:
    data = fetch_json(COMPANY_TICKERS_URL)
    out: dict[str, str] = {}
    for record in data.values():
        ticker = str(record["ticker"]).upper()
        out[ticker] = str(record["cik_str"]).zfill(10)
    return out


def latest_10k_metadata(
    ticker: str, cik_map: dict[str, str] | None = None
) -> dict[str, Any] | None:
    cmap = ticker_cik_map() if cik_map is None else cik_map
    cik = cmap.get(ticker.upper())
    if not cik:
        return None
    sub = fetch_json(SUBMISSIONS_URL.format(cik=cik))
    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    for idx, form in enumerate(forms):
        if form not in ANNUAL_FORMS:
            continue
        accession = recent["accessionNumber"][idx]
        document = recent["primaryDocument"][idx]
        url = ARCHIVES_URL.format(
            cik_int=str(int(cik)),
            accession_nodash=accession.replace("-", ""),
            document=document,
        )
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "form": form,
            "accession": accession,
            "filing_date": recent["filingDate"][idx],
            "report_date": recent["reportDate"][idx],
            "document": document,
            "filing_url": url,
        }
    return None


def fetch_latest_10k_text(
    ticker: str, cik_map: dict[str, str] | None = None
) -> dict[str, Any]:
    meta = latest_10k_metadata(ticker, cik_map)
    if meta is None:
        return {
            "ticker": ticker.upper(),
            "filing_text": None,
            "filing_url": None,
            "error": "annual filing not found",
        }
    try:
        text = fetch_text(meta["filing_url"])
    except Exception as exc:
        return {**meta, "filing_text": None, "error": str(exc)}
    return {**meta, "filing_text": text, "error": None}


def recent_forms(
    ticker: str,
    *,
    forms: set[str] | None = None,
    since: str | None = None,
    until: str | None = None,
    cik_map: dict[str, str] | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    """Return dated SEC form filings (default 8-K/6-K) with archive locators."""
    wanted = forms or EVENT_FORMS
    cmap = ticker_cik_map() if cik_map is None else cik_map
    cik = cmap.get(ticker.upper())
    if not cik:
        return []
    try:
        sub = fetch_json(SUBMISSIONS_URL.format(cik=cik))
    except Exception:
        return []
    recent = sub.get("filings", {}).get("recent", {})
    form_list = recent.get("form", []) or []
    out: list[dict[str, Any]] = []
    for idx, form in enumerate(form_list):
        if form not in wanted:
            continue
        filing_date = recent.get("filingDate", [None] * (idx + 1))[idx]
        if not filing_date or (since and filing_date < since) or (until and filing_date > until):
            continue
        accession = recent["accessionNumber"][idx]
        document = recent["primaryDocument"][idx]
        url = ARCHIVES_URL.format(
            cik_int=str(int(cik)),
            accession_nodash=accession.replace("-", ""),
            document=document,
        )
        primary_desc = ""
        try:
            primary_desc = (recent.get("primaryDocDescription") or [""] * (idx + 1))[idx] or ""
        except Exception:
            primary_desc = ""
        title = f"SEC {form}" + (f": {primary_desc}" if primary_desc else "")
        out.append(
            {
                "ticker": ticker.upper(),
                "date": filing_date[:10],
                "kind": "8-K",
                "title": title[:300],
                "locator": url,
                "source": "sec_edgar",
                "role": "sec_event",
                "form": form,
                "accession": accession,
                "cik": cik,
            }
        )
        if len(out) >= limit:
            break
    return out


def _strip_tags(raw: str) -> str:
    no_scripts = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", no_scripts)
    return re.sub(r"\s+", " ", text).strip()
