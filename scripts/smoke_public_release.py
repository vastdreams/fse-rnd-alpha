#!/usr/bin/env python3
"""Authenticated black-box smoke for a deployed public investor platform."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = Request(f"{base_url.rstrip('/')}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def require(status: int, actual: int, body: Any, operation: str) -> Any:
    if actual != status:
        raise RuntimeError(f"{operation} expected HTTP {status}, got {actual}: {body}")
    return body


def login(base_url: str, email: str, password: str) -> str:
    status, body = request(
        base_url, "POST", "/api/auth/login", body={"email": email, "password": password}
    )
    data = require(200, status, body, f"login for {email}")
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"login for {email} returned no access token")
    return token


def vector_claim_ids(value: Any) -> list[str]:
    if isinstance(value, dict):
        ids = value.get("claim_ids")
        if isinstance(ids, list) and ids:
            return [str(claim_id) for claim_id in ids if claim_id]
        for child in value.values():
            found = vector_claim_ids(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = vector_claim_ids(child)
            if found:
                return found
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--second-email", required=True)
    parser.add_argument("--second-password", required=True)
    args = parser.parse_args()

    first_token = login(args.base_url, args.email, args.password)
    second_token = login(args.base_url, args.second_email, args.second_password)
    first_headers = first_token

    status, body = request(args.base_url, "GET", "/ready")
    ready = require(200, status, body, "readiness")
    if ready.get("ready") is not True:
        raise RuntimeError(f"readiness payload is not ready: {ready}")

    status, body = request(args.base_url, "GET", "/api/universe/rank", token=first_headers)
    rank = require(200, status, body, "rank")
    universe_version = rank.get("universe_version")
    rows = rank.get("rows") or []
    if not universe_version or not rows:
        raise RuntimeError("rank response has no immutable universe version or eligible rows")
    ticker = rows[0]["ticker"]
    encoded_version = urlencode({"universe_version": universe_version})

    dcf = require(
        200,
        *request(args.base_url, "GET", f"/api/universe/stances?{encoded_version}", token=first_headers),
        "stances",
    )
    status, body = request(
        args.base_url,
        "GET",
        f"/api/universe/company/{ticker}?{encoded_version}",
        token=first_headers,
    )
    company = require(200, status, body, "company research")
    require(
        200,
        *request(args.base_url, "GET", f"/api/universe/financials/{ticker}", token=first_headers),
        "financials",
    )
    require(
        200,
        *request(args.base_url, "GET", f"/api/universe/price-history/{ticker}", token=first_headers),
        "price history",
    )

    require(
        200,
        *request(
            args.base_url,
            "POST",
            f"/api/universe/dcf/{ticker}?save=true&{encoded_version}",
            token=first_headers,
            body={
                "ticker": ticker,
                "scenario": "custom",
                "growth": 0.05,
                "wacc": 0.10,
                "terminal_g": 0.03,
                "years": 10,
                "glide_years": 7,
            },
        ),
        "DCF save",
    )
    dcf_run_id = dcf.get("run_id")
    if not dcf_run_id:
        raise RuntimeError("saved DCF returned no immutable run identifier")

    claim_ids = vector_claim_ids(company.get("vector"))
    if not claim_ids:
        raise RuntimeError(f"{ticker} has no evidence claim bound to its frozen vector")
    memo = require(
        200,
        *request(
            args.base_url,
            "POST",
            f"/api/universe/memo/{ticker}",
            token=first_headers,
            body={
                "thesis": "Release smoke: citation is bound to the immutable research vector.",
                "citations": [claim_ids[0]],
                "universe_version": universe_version,
            },
        ),
        "memo save",
    )
    memo_id = memo.get("memo_id")
    if not memo_id:
        raise RuntimeError("saved memo returned no immutable memo identifier")
    memos = require(
        200,
        *request(
            args.base_url,
            "GET",
            f"/api/universe/memo/{ticker}?{encoded_version}",
            token=first_headers,
        ),
        "memo reload",
    )
    if not memos.get("memos") or not memos["memos"][0].get("citation_records"):
        raise RuntimeError("memo reload did not return the cited evidence record")

    created = require(
        200,
        *request(
            args.base_url,
            "POST",
            "/api/books",
            token=first_headers,
            body={
                "name": f"Release smoke {datetime.now(timezone.utc).isoformat()}",
                "universe_version": universe_version,
            },
        ),
        "book create",
    )
    book_id = created["book_id"]
    holding = {
        "ticker": ticker,
        "weight_pct": 10,
        "added_at": datetime.now(timezone.utc).isoformat(),
        # The test must never weaken a real research gate; this is a recorded
        # per-holding acknowledgement to exercise the constrained path.
        "override_reason": "Release smoke acknowledgement",
    }
    require(
        200,
        *request(
            args.base_url,
            "PUT",
            f"/api/books/{book_id}",
            token=first_headers,
            body={"holdings": [holding]},
        ),
        "book save",
    )
    require(
        200,
        *request(
            args.base_url,
            "POST",
            f"/api/books/{book_id}/lock",
            token=first_headers,
            body={"acknowledgements": [ticker]},
        ),
        "book lock",
    )
    require(
        200,
        *request(
            args.base_url, "GET", f"/api/books/{book_id}/audit-pack", token=first_headers
        ),
        "book audit export",
    )

    other_books = require(
        200, *request(args.base_url, "GET", "/api/books", token=second_token), "second-user books"
    )
    if any(book["book_id"] == book_id for book in other_books.get("books", [])):
        raise RuntimeError("second user can see the first user's book")
    other_company = require(
        200,
        *request(
            args.base_url,
            "GET",
            f"/api/universe/company/{ticker}?{encoded_version}",
            token=second_token,
        ),
        "second-user company research",
    )
    if any(run.get("run_id") == dcf_run_id for run in other_company.get("dcf_runs", [])):
        raise RuntimeError("second user can see the first user's private DCF")
    other_memos = require(
        200,
        *request(
            args.base_url,
            "GET",
            f"/api/universe/memo/{ticker}?{encoded_version}",
            token=second_token,
        ),
        "second-user memos",
    )
    if any(memo.get("memo_id") == memo_id for memo in other_memos.get("memos", [])):
        raise RuntimeError("second user can see the first user's private memo")
    status, body = request(args.base_url, "GET", "/api/universe/admin/kpis", token=second_token)
    require(403, status, body, "public admin denial")

    require(
        200,
        *request(args.base_url, "DELETE", f"/api/books/{book_id}", token=first_headers),
        "smoke book cleanup",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "ticker": ticker,
                "universe_version": universe_version,
                "checked": [
                    "auth",
                    "rank",
                    "stances",
                    "company",
                    "financials",
                    "price",
                    "dcf",
                    "memo",
                    "book",
                    "two-user-isolation",
                    "admin-denial",
                ],
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"release smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
