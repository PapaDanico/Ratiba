"""Audit pack storage backend — S3-compatible with local-FS fallback.

When ``AUDIT_PACK_S3_BUCKET`` is set, packs are written to and read from
S3-compatible object storage (supports ADC Nairobi's S3-compatible
offering as well as AWS / DigitalOcean Spaces / MinIO via the
``AUDIT_PACK_S3_ENDPOINT`` override). Otherwise packs live on the local
filesystem under ``AUDIT_PACK_DIR`` — fine for the pilot and for tests.

The storage_path returned to the caller is opaque (``s3://bucket/key``
or an absolute filesystem path); :func:`read_bytes` knows how to read
each shape back.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings

log = logging.getLogger("ratiba.audit_pack_storage")


def _s3_client() -> Any:
    """Lazy import so dev/test envs without boto3 don't import-fail."""
    import boto3

    settings = get_settings()
    kwargs: dict[str, str] = {}
    if settings.audit_pack_s3_endpoint:
        kwargs["endpoint_url"] = settings.audit_pack_s3_endpoint
    if settings.audit_pack_s3_region:
        kwargs["region_name"] = settings.audit_pack_s3_region
    return boto3.client("s3", **kwargs)


def write(filename: str, content: bytes) -> str:
    """Persist ``content`` under ``filename`` and return the storage path.

    Falls back to local FS if the S3 bucket isn't configured.
    """
    settings = get_settings()
    if settings.audit_pack_s3_bucket:
        key = filename
        _s3_client().put_object(
            Bucket=settings.audit_pack_s3_bucket,
            Key=key,
            Body=content,
            ContentType="application/pdf",
        )
        return f"s3://{settings.audit_pack_s3_bucket}/{key}"

    out_dir = Path(settings.audit_pack_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_bytes(content)
    return str(path)


def read_bytes(storage_path: str) -> bytes | None:
    """Return the bytes at ``storage_path`` or ``None`` if missing."""
    if storage_path.startswith("s3://"):
        _, _, rest = storage_path.partition("s3://")
        bucket, _, key = rest.partition("/")
        try:
            obj = _s3_client().get_object(Bucket=bucket, Key=key)
        except Exception as exc:
            log.warning("S3 read failed: %r", exc)
            return None
        return bytes(obj["Body"].read())

    path = Path(storage_path)
    if not path.exists():
        return None
    return path.read_bytes()
