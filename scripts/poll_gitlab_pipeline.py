#!/usr/bin/env python3
"""
PATH: scripts/poll_gitlab_pipeline.py
PURPOSE: Poll a GitLab pipeline until publish jobs succeed (or fail).

Handles control characters in glab/API JSON that previously caused silent
false-success polls (exit 0 with empty flag).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any


PUBLISH_JOBS = ("publish_immutable_images", "publish_release_bundle")


def scrub(raw: str) -> str:
    return "".join(ch if ord(ch) >= 32 or ch in "\n\r\t" else " " for ch in raw)


def api(path: str) -> Any:
    proc = subprocess.run(
        ["glab", "api", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"glab api failed ({proc.returncode}): {proc.stderr or proc.stdout}")
    return json.loads(scrub(proc.stdout))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="vastdreams%2Ffse-research")
    ap.add_argument("--pipeline", type=int, required=True)
    ap.add_argument("--interval", type=int, default=40)
    ap.add_argument("--max-polls", type=int, default=40)
    ap.add_argument("--cancel-pipeline", type=int, default=None)
    args = ap.parse_args()

    if args.cancel_pipeline:
        try:
            d = api(f"projects/{args.project}/pipelines/{args.cancel_pipeline}/cancel")
            # POST via glab needs --method; best-effort
        except SystemExit:
            subprocess.run(
                [
                    "glab",
                    "api",
                    "--method",
                    "POST",
                    f"projects/{args.project}/pipelines/{args.cancel_pipeline}/cancel",
                ],
                check=False,
            )

    for i in range(1, args.max_polls + 1):
        jobs = api(f"projects/{args.project}/pipelines/{args.pipeline}/jobs")
        rows = sorted(jobs, key=lambda j: (j.get("stage", ""), j.get("name", "")))
        print(f"=== poll {i} ===")
        for j in rows:
            print(f"{j.get('status', '?'):12} {j.get('stage', '?'):12} {j.get('name')}")
        if any(j.get("status") == "failed" for j in jobs):
            print("FAILED", file=sys.stderr)
            raise SystemExit(2)
        pub = [j for j in jobs if j.get("name") in PUBLISH_JOBS]
        if pub and all(j.get("status") == "success" for j in pub):
            print("PUBLISHED")
            raise SystemExit(0)
        time.sleep(args.interval)
    print("TIMEOUT", file=sys.stderr)
    raise SystemExit(3)


if __name__ == "__main__":
    main()
