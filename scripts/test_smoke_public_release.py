#!/usr/bin/env python3
"""Exercise the deployed-release smoke contract against an in-process API."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


SOURCE_SHA = "a" * 40
MANIFEST_SHA = "b" * 64


class SmokeHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, str]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def _write(self, status: int, body: dict[str, object]) -> None:
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        self.requests.append(("GET", path))
        if path == "/ready":
            self._write(
                200,
                {
                    "ready": True,
                    "release": {
                        "source_sha": SOURCE_SHA,
                        "data_manifest_sha256": MANIFEST_SHA,
                    },
                },
            )
        elif path == "/api/universe/rank":
            self._write(
                200,
                {
                    "universe_version": "univ_fixture",
                    "rows": [{"ticker": "FIXT"}],
                },
            )
        elif path == "/api/universe/stances":
            self._write(200, {"rows": []})
        elif path == "/api/universe/company/FIXT":
            self._write(
                200,
                {
                    "vector": {"fair_px_med": {"claim_ids": ["claim-fixture"]}},
                    "dcf_runs": [],
                },
            )
        elif path == "/api/universe/financials/FIXT":
            self._write(200, {"annual": [], "quarterly": []})
        elif path == "/api/universe/price-history/FIXT":
            self._write(200, {"bars": []})
        elif path == "/api/universe/memo/FIXT":
            is_second_user = self.headers.get("Authorization") == "Bearer second-token"
            self._write(
                200,
                {
                    "memos": []
                    if is_second_user
                    else [
                        {
                            "memo_id": "memo-fixture",
                            "citation_records": [{"claim_id": "claim-fixture"}],
                        }
                    ]
                },
            )
        elif path == "/api/books/book-fixture/audit-pack":
            self._write(200, {"book_id": "book-fixture", "holdings": []})
        elif path == "/api/books":
            self._write(200, {"books": []})
        elif path == "/api/universe/admin/kpis":
            self._write(403, {"detail": "admin only"})
        else:
            self._write(404, {"detail": f"unexpected GET {path}"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        self.requests.append(("POST", path))
        if path == "/api/auth/login":
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length) or b"{}")
            token = "second-token" if payload.get("email") == "second@example.test" else "first-token"
            self._write(200, {"access_token": token})
        elif path == "/api/universe/dcf/FIXT":
            self._write(
                200,
                {
                    "run_id": "dcf-fixture",
                    "outputs": {"fair_px_med": 125.0},
                },
            )
        elif path == "/api/universe/memo/FIXT":
            self._write(200, {"memo_id": "memo-fixture"})
        elif path == "/api/books":
            self._write(200, {"book_id": "book-fixture"})
        elif path == "/api/books/book-fixture/lock":
            self._write(200, {"locked": True})
        else:
            self._write(404, {"detail": f"unexpected POST {path}"})

    def do_PUT(self) -> None:
        self.requests.append(("PUT", urlparse(self.path).path))
        if urlparse(self.path).path == "/api/books/book-fixture":
            self._write(200, {"saved": True})
        else:
            self._write(404, {"detail": "unexpected PUT"})

    def do_DELETE(self) -> None:
        self.requests.append(("DELETE", urlparse(self.path).path))
        if urlparse(self.path).path == "/api/books/book-fixture":
            self._write(409, {"detail": "Locked or exported books are immutable"})
        else:
            self._write(404, {"detail": "unexpected DELETE"})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), SmokeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="smoke-public-release-test.") as directory:
            evidence_path = Path(directory) / "evidence.json"
            root = Path(__file__).resolve().parent.parent
            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "smoke_public_release.py"),
                    "--base-url",
                    f"http://127.0.0.1:{server.server_port}",
                    "--expected-source-sha",
                    SOURCE_SHA,
                    "--expected-data-manifest-sha256",
                    MANIFEST_SHA,
                    "--evidence-file",
                    str(evidence_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "RELEASE_SMOKE_EMAIL": "first@example.test",
                    "RELEASE_SMOKE_PASSWORD": "password",
                    "RELEASE_SMOKE_SECOND_EMAIL": "second@example.test",
                    "RELEASE_SMOKE_SECOND_PASSWORD": "password",
                },
            )
            if completed.returncode:
                raise AssertionError(
                    "smoke command failed:\n"
                    f"stdout:\n{completed.stdout}\n"
                    f"stderr:\n{completed.stderr}\n"
                    f"requests:\n{SmokeHandler.requests}"
                )
            output = json.loads(completed.stdout)
            evidence = json.loads(evidence_path.read_text())
            assert output == evidence
            assert evidence["source_sha"] == SOURCE_SHA
            assert evidence["data_manifest_sha256"] == MANIFEST_SHA
            assert evidence["checked"][-3:] == [
                "locked-book-retention",
                "two-user-isolation",
                "admin-denial",
            ]
    finally:
        server.shutdown()
        server.server_close()

    print("Authenticated public release smoke contract passed.")


if __name__ == "__main__":
    main()
