"""
PATH: backend/app/contracts/paths.py
PURPOSE: Resolve the sealed contracts/ directory in local checkout and Docker images.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def contracts_dir() -> Path:
    """Return the directory that holds decision-chains.json / formula-registry.json.

    Local checkout: ``<repo>/contracts`` (``__file__`` is under ``backend/app/contracts``).
    Docker image: ``/app/contracts`` (baked next to the app package at image build).
    """

    here = Path(__file__).resolve()
    candidates = (
        Path("/app/contracts"),
        here.parents[3] / "contracts",  # <repo>/contracts
        here.parents[2] / "contracts",  # /app/contracts if laid out flat
    )
    for path in candidates:
        if (path / "decision-chains.json").is_file() and (
            path / "formula-registry.json"
        ).is_file():
            return path
    tried = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(
        "Sealed investor contracts not found. Looked for decision-chains.json and "
        f"formula-registry.json under: {tried}. Backend images must COPY "
        "contracts/ to /app/contracts (build from repo root with "
        "`docker build -f backend/Dockerfile .`)."
    )
