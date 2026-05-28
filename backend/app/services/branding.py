"""Shared DN Consultancy brand assets for generated documents.

The logo is inlined into PDFs as a base64 data URI so the rendered
documents stay fully self-contained and portable (no external fetch).
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

_LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "dn_logo.png"


@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    """Return the DN Consultancy logo as a ``data:image/png;base64,…`` URI."""
    encoded = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
