"""KCAA-presentable audit pack PDF generator.

Phase 0 skeleton only. WeasyPrint template + DN branding land in Phase 5.
"""

from __future__ import annotations


class AuditPackNotImplemented(NotImplementedError):
    """Raised by Phase 0 stubs to make the deferral obvious."""


def generate_pack(*_args: object, **_kwargs: object) -> bytes:
    """Phase 5 entry point — produce a signed PDF audit pack."""
    raise AuditPackNotImplemented("Audit pack generator arrives in Phase 5")
