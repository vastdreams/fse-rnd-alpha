"""
PATH: backend/app/services/report_artifact_store.py
PURPOSE: Content-addressed storage for rendered report artifacts (PDF/JSON).

S3 (Object-Lock bucket) when REPORT_ARTIFACT_BUCKET is set; otherwise a local
directory for development. Keys are derived from the artifact sha256 so a
re-render of identical content is a no-op.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional


class ArtifactStoreError(Exception):
    pass


def artifact_key(snapshot_id: str, kind: str, sha256: str) -> str:
    ext = "pdf" if kind == "pdf" else "json"
    return f"company-reports/{snapshot_id}/{sha256}.{ext}"


def _bucket() -> Optional[str]:
    return os.environ.get("REPORT_ARTIFACT_BUCKET") or None


def _local_root() -> Path:
    return Path(os.environ.get("REPORT_ARTIFACT_DIR", "/opt/rd-alpha-artifacts"))


def store_artifact(snapshot_id: str, kind: str, content: bytes) -> tuple[str, str]:
    """Persist bytes; return (storage_key, sha256). Idempotent by content."""
    sha256 = hashlib.sha256(content).hexdigest()
    key = artifact_key(snapshot_id, kind, sha256)
    bucket = _bucket()
    if bucket:
        import boto3

        client = boto3.client("s3")
        content_type = "application/pdf" if kind == "pdf" else "application/json"
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            ChecksumAlgorithm="SHA256",
        )
        return key, sha256
    path = _local_root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    return key, sha256


def load_artifact(storage_key: str, expected_sha256: str) -> bytes:
    """Fetch bytes and verify the ledger checksum before serving."""
    bucket = _bucket()
    if bucket:
        import boto3

        client = boto3.client("s3")
        body = client.get_object(Bucket=bucket, Key=storage_key)["Body"].read()
    else:
        path = _local_root() / storage_key
        if not path.is_file():
            raise ArtifactStoreError(f"Artifact missing: {storage_key}")
        body = path.read_bytes()
    actual = hashlib.sha256(body).hexdigest()
    if actual != expected_sha256:
        raise ArtifactStoreError(
            f"Artifact checksum mismatch for {storage_key}: expected {expected_sha256}, got {actual}"
        )
    return body
