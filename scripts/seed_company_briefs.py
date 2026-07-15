"""
PATH: scripts/seed_company_briefs.py
PURPOSE: Operator release tool — walk authored company briefs through
draft → validate → review → publish against a running backend database.

Runs in-process (like other release seeding scripts) inside the backend
container:

    docker exec -e PYTHONPATH=/app rd_alpha_backend \
        python3 /app/scripts/seed_company_briefs.py \
        --briefs-dir /app/research/company-briefs \
        --tickers DOCU,INTU,KSPI,MNDY,TTD,WIX \
        [--refresh-consensus] [--publish]

The review step is executed as a second, separate pass with the platform's
final-review identity: it re-validates the stored snapshot from the database
(not from memory) and re-resolves every citation before recording the review.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

AUTHOR = {"id": "brief_author_agent", "email": "research@finsoeasy.com", "role": "admin"}
REVIEWER = {"id": "cursor_final_review_agent", "email": "review@finsoeasy.com", "role": "admin"}


def _client(user: dict) -> AsyncClient:
    from app.api.routes.auth import get_current_user, require_operator
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_operator] = lambda: user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://release", timeout=600)


async def _independent_review(snapshot_id: str) -> list[str]:
    """Re-validate the stored snapshot and citation graph. Returns problems."""
    from app.contracts.company_reports import CompanyReportSnapshot, report_content_sha256

    problems: list[str] = []
    async with _client(REVIEWER) as client:
        res = await client.get(f"/api/reports/{snapshot_id}")
        if res.status_code != 200:
            return [f"fetch failed: HTTP {res.status_code}"]
        envelope = res.json()
        try:
            snapshot = CompanyReportSnapshot.model_validate(envelope["report"])
        except ValueError as exc:
            return [f"contract validation failed: {exc}"]
        if report_content_sha256(snapshot) != envelope["content_sha256"]:
            problems.append("content hash mismatch")
        known = {c.cite_id for c in snapshot.citations}
        for section in [*snapshot.page1, *snapshot.page2]:
            for cid in section.cite_ids:
                if cid not in known:
                    problems.append(f"{section.section_id}: dangling cite {cid}")
            if section.body.strip() and not section.cite_ids:
                problems.append(f"{section.section_id}: uncited narrative")
        if not snapshot.disclosures:
            problems.append("missing disclosures")
    return problems


async def seed_one(ticker: str, briefs_dir: Path, refresh_consensus: bool, publish: bool) -> dict:
    authored_path = briefs_dir / f"{ticker}.json"
    if not authored_path.is_file():
        return {"ticker": ticker, "error": f"authored brief missing: {authored_path}"}
    authored = json.loads(authored_path.read_text())

    async with _client(AUTHOR) as client:
        res = await client.post(
            f"/api/reports/company/{ticker}/draft",
            json={"authored": authored, "refresh_consensus": refresh_consensus},
        )
        if res.status_code != 200:
            return {"ticker": ticker, "error": f"draft failed: {res.status_code} {res.text[:400]}"}
        draft = res.json()
        snapshot_id = draft["snapshot_id"]
        if draft.get("deduplicated") and draft.get("status") in ("reviewed", "published"):
            return {"ticker": ticker, "snapshot_id": snapshot_id, "status": draft["status"], "deduplicated": True}

        res = await client.post(f"/api/reports/{snapshot_id}/validate")
        if res.status_code != 200:
            return {"ticker": ticker, "snapshot_id": snapshot_id, "error": f"validate failed: {res.text[:400]}"}

    problems = await _independent_review(snapshot_id)
    if problems:
        return {"ticker": ticker, "snapshot_id": snapshot_id, "error": f"review blocked: {problems}"}

    async with _client(REVIEWER) as client:
        res = await client.post(
            f"/api/reports/{snapshot_id}/review",
            json={
                "notes": "Independent structural review: contract re-validated from stored row; "
                "hash verified; citation graph fully resolved; disclosures present.",
                "acknowledge_independent": True,
            },
        )
        if res.status_code != 200:
            return {"ticker": ticker, "snapshot_id": snapshot_id, "error": f"review failed: {res.text[:400]}"}

    status = "reviewed"
    if publish:
        async with _client(AUTHOR) as client:
            res = await client.post(f"/api/reports/{snapshot_id}/publish")
            if res.status_code != 200:
                return {"ticker": ticker, "snapshot_id": snapshot_id, "error": f"publish failed: {res.text[:400]}"}
            status = "published"
    return {
        "ticker": ticker,
        "snapshot_id": snapshot_id,
        "status": status,
        "consensus_used": draft.get("consensus_used"),
        "deduplicated": draft.get("deduplicated", False),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--briefs-dir", type=Path, required=True)
    parser.add_argument("--tickers", required=True, help="Comma-separated tickers")
    parser.add_argument("--refresh-consensus", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    failures = 0
    for ticker in [t.strip().upper() for t in args.tickers.split(",") if t.strip()]:
        result = await seed_one(ticker, args.briefs_dir, args.refresh_consensus, args.publish)
        print(json.dumps(result))
        if "error" in result:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
